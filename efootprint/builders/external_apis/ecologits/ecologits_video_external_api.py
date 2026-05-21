import math
import re
from typing import List

from ecologits.electricity_mix_repository import electricity_mixes
from ecologits.estimations.video import (
    _HARDWARE_CONFIGURATIONS, _MODELS_INFO, _PROVIDER_CONFIGURATIONS, duration_to_frames, parse_value_or_range)
from ecologits.impacts.video import compute_video_impacts_dag, dag as video_dag
from ecologits.utils.range_value import RangeValue

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_utils import (
    ECOLOGITS_VIDEO_DEPENDENCY_GRAPH, create_update_method_for_ecologits_attribute, mean_value_or_range)
from efootprint.builders.external_apis.ecologits.ecologits_external_api_server_base import (
    EcoLogitsExternalAPIServerBase)
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI
from efootprint.builders.external_apis.external_api_job_base_class import ExternalAPIJob
from efootprint.constants.sources import Sources
from efootprint.constants.units import u


ecologits_video_defaults_source = Source(
    "Ecologits video_impacts defaults",
    "https://github.com/mlco2/ecologits/tree/main/ecologits/estimations/video.py")
compute_video_impacts_dag_source = Source(
    "Ecologits compute_video_impacts_dag function",
    "https://github.com/mlco2/ecologits/tree/main/ecologits/impacts/video.py")


ecologits_video_calculated_attributes = [
    elt for elt in ECOLOGITS_VIDEO_DEPENDENCY_GRAPH.keys() if elt in ECOLOGITS_UNIT_MAPPING
    and not elt.endswith("_wue") and not elt.endswith("_pe") and not elt.endswith("_adpe")]


_RESOLUTION_LABELS = {
    (854, 480): "480p (854 x 480)",
    (1024, 576): "576p (1024 x 576)",
    (1280, 720): "720p (1280 x 720)",
    (1920, 1080): "1080p (1920 x 1080)",
    (3840, 2160): "4K (3840 x 2160)",
}


def _format_resolution_label(width: int, height: int) -> str:
    if (width, height) not in _RESOLUTION_LABELS:
        raise ValueError(
            f"Resolution {width}x{height} has no label in _RESOLUTION_LABELS. "
            f"EcoLogits likely added a new catalog resolution; add an entry above.")
    return _RESOLUTION_LABELS[(width, height)]


def _parse_resolution_label(label: str) -> tuple[int, int]:
    match = re.search(r"\((\d+)\s*x\s*(\d+)\)", label)
    if not match:
        raise ValueError(f"Invalid resolution label: {label!r}")
    return int(match.group(1)), int(match.group(2))


_sorted_provider_names = sorted({slug.split("/", 1)[0] for slug in _MODELS_INFO})


class EcoLogitsVideoGenExternalAPIServer(EcoLogitsExternalAPIServerBase):
    """Virtual server backing an {class:EcoLogitsVideoGenExternalAPI}. Aggregates per-request fabrication and energy footprints emitted by the underlying EcoLogits video model into hourly footprints."""

    param_descriptions = {}


class EcoLogitsVideoGenExternalAPI(ExternalAPI):
    """An external generative-AI **video** API (Sora, Veo, Kling, Seedance, Runway, ...) modeled through the EcoLogits library. Picks a provider and model from the EcoLogits video catalog; datacenter location, PUE and WUE are looked up in the EcoLogits per-provider config."""

    interactions = (
        "Pick {param:EcoLogitsVideoGenExternalAPI.provider} and {param:EcoLogitsVideoGenExternalAPI.model_name} "
        "from the EcoLogits video catalog, then attach {class:EcoLogitsVideoGenExternalAPIJob}s sized by "
        "resolution, duration and whether audio is generated.")

    param_descriptions = {
        "provider": (
            "Provider key parsed from the EcoLogits video catalog (e.g. openai, google, klingai)."),
        "model_name": (
            "Specific video model name (after the provider/ prefix) from the chosen provider's EcoLogits video "
            "catalog. Drives the hardware configuration and the latency-regression coefficients."),
    }

    server_class = EcoLogitsVideoGenExternalAPIServer

    default_values = {
        "provider": SourceObject("openai", source=ecologits_video_defaults_source),
        "model_name": SourceObject("sora-2-pro", source=ecologits_video_defaults_source),
    }

    list_values = {
        "provider": [SourceObject(p) for p in _sorted_provider_names],
    }

    @staticmethod
    def generate_conditional_list_values(list_values):
        values = {}
        for provider in list_values["provider"]:
            values[provider] = [
                SourceObject(slug.split("/", 1)[1]) for slug in _MODELS_INFO
                if slug.split("/", 1)[0] == provider.value]
        return {"model_name": {"depends_on": "provider", "conditional_list_values": values}}

    conditional_list_values = generate_conditional_list_values(list_values)

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject):
        super().__init__(name=name)
        self.provider = provider.set_label("Provider")
        self.model_name = model_name.set_label("Model used")
        self.datacenter_location = EmptyExplainableObject()
        self.data_center_pue = EmptyExplainableObject()
        self.average_carbon_intensity = EmptyExplainableObject()

    calculated_attributes: List[str] = ExternalAPI.calculated_attributes + [
        "datacenter_location", "data_center_pue", "average_carbon_intensity"]

    def update_datacenter_location(self) -> None:
        """Geographic zone where the provider's datacenter runs, looked up in the EcoLogits video provider config. Drives which electricity mix is applied."""
        datacenter_location = _PROVIDER_CONFIGURATIONS[self.provider.value]["datacenter_location"]
        self.datacenter_location = ExplainableObject(
            datacenter_location,
            f"Datacenter location for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits video provider config",
            source=ecologits_video_defaults_source,
        )

    def update_data_center_pue(self) -> None:
        """Power Usage Effectiveness of the provider's datacenter, looked up in the EcoLogits video provider config."""
        datacenter_pue = mean_value_or_range(
            parse_value_or_range(_PROVIDER_CONFIGURATIONS[self.provider.value]["datacenter_pue"]))
        self.data_center_pue = ExplainableQuantity(
            datacenter_pue * u.dimensionless,
            f"Datacenter PUE for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits video provider config",
            source=ecologits_video_defaults_source,
        )

    def update_average_carbon_intensity(self) -> None:
        """Average grid carbon intensity at the datacenter location, looked up in the EcoLogits electricity mix repository."""
        electricity_mix_zone = self.datacenter_location.value
        if_electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)
        if if_electricity_mix is None:
            raise ValueError(f"Could not find electricity mix for `{electricity_mix_zone}` zone.")
        self.average_carbon_intensity = ExplainableQuantity(
            if_electricity_mix.gwp * ECOLOGITS_UNIT_MAPPING["if_electricity_mix_gwp"],
            f"Average carbon intensity of electricity mix for {self.provider}",
            left_parent=self.datacenter_location,
            operator="query EcoLogits electricity mix repository with datacenter location",
            source=ecologits_video_defaults_source,
        )


class EcoLogitsVideoGenExternalAPIJob(ExternalAPIJob):
    """One generation call against an {class:EcoLogitsVideoGenExternalAPI}, sized by resolution, duration, and whether audio is generated. Per-request energy and embodied GWP are computed from the EcoLogits video impact DAG."""

    param_descriptions = {
        "external_api": (
            "{class:EcoLogitsVideoGenExternalAPI} the call is routed to."),
        "resolution": (
            "Output resolution as a label like \"1080p (1920 x 1080)\". The width and height are parsed from "
            "this string and fed to the EcoLogits video DAG."),
        "duration": (
            "Length of the generated video in seconds. Drives frame count, generation latency, and the "
            "resulting energy and embodied GWP through the EcoLogits video impact model."),
        "with_audio": (
            "Whether audio is generated alongside the video. When False, EcoLogits applies the model's "
            "calibrated non_audio_weight scaling to the latency regression."),
    }

    default_values = {
        "resolution": SourceObject("720p (1280 x 720)"),
        "duration": SourceValue(8 * u.s),
        "with_audio": SourceObject(True),
    }

    @staticmethod
    def generate_conditional_list_values():
        values = {}
        for slug, info in _MODELS_INFO.items():
            model_short = slug.split("/", 1)[1]
            values[SourceObject(model_short)] = [
                SourceObject(_format_resolution_label(w, h))
                for w, h in info["capabilities"]["resolutions"]]
        return {"resolution": {"depends_on": "external_api.model_name", "conditional_list_values": values}}

    conditional_list_values = generate_conditional_list_values()

    def __init__(self, name: str, external_api: EcoLogitsVideoGenExternalAPI, resolution: ExplainableObject,
                 duration: ExplainableQuantity, with_audio: ExplainableObject):
        super().__init__(name=name, external_api=external_api, data_transferred=SourceValue(0 * u.MB),
                         data_stored=SourceValue(0 * u.MB_stored), request_duration=SourceValue(0 * u.s),
                         compute_needed=SourceValue(0 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        self.resolution = resolution.set_label("Resolution")
        self.duration = duration.set_label("Video duration")
        self.with_audio = with_audio.set_label("Generates audio")

        self.hourly_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.impacts = EmptyExplainableObject()
        for ecologits_attr in ecologits_video_calculated_attributes:
            setattr(self, ecologits_attr, EmptyExplainableObject())

    calculated_attributes: List[str] = (
        ["data_transferred", "impacts"] + ecologits_video_calculated_attributes
        + ["request_duration"]
        + ExternalAPIJob.calculated_attributes
        + ["hourly_occurrences_across_usage_patterns"])

    def update_data_transferred(self):
        """Data transferred per call, estimated as duration × bits_per_pixel × pixel_count × fps. The bits_per_pixel and fps values are local hypotheses constructed fresh inside this method so they don't become shared nodes across the calculation graph."""
        bits_per_pixel = ExplainableQuantity(0.1 * u.bit, "Bits per pixel", source=Sources.HYPOTHESIS)
        fps = ExplainableQuantity(24 / u.s, "Frames per second", source=Sources.HYPOTHESIS)
        width, height = _parse_resolution_label(self.resolution.value)
        pixel_count = ExplainableQuantity(
            width * height * u.dimensionless, f"pixel count for resolution {self.resolution}",
            left_parent=self.resolution, operator="pixel count computation")
        self.data_transferred = (self.duration * bits_per_pixel * pixel_count * fps).to(u.MB).set_label(
            f"Data transferred for {self.external_api.model_name}")

    def update_request_duration(self):
        """Request duration of one call, equal to the generation latency derived from EcoLogits."""
        self.request_duration = self.generation_latency.copy()

    def update_hourly_occurrences_across_usage_patterns(self):
        """Hourly count of occurrences of this job summed across all usage patterns that trigger it."""
        self.hourly_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_occurrences_per_usage_pattern", "occurrences")

    def _resolve_model_info(self) -> dict:
        slug = f"{self.external_api.provider.value}/{self.external_api.model_name.value}"
        info = _MODELS_INFO.get(slug)
        if info is None:
            raise ValueError(f"Could not find video model `{slug}` in EcoLogits video catalog.")
        return info

    def update_impacts(self) -> None:
        """Cached EcoLogits video impact dictionary for one call, computed by running the EcoLogits video DAG against the chosen model, resolution, duration, audio flag, and datacenter assumptions. Subsequent updates extract individual fields from this dictionary."""
        # Local datacenter_wue: feeds water only (out of GWP scope) and must not become a shared graph node.
        datacenter_wue = mean_value_or_range(
            parse_value_or_range(_PROVIDER_CONFIGURATIONS[self.external_api.provider.value]["datacenter_wue"]))

        info = self._resolve_model_info()
        width, height = _parse_resolution_label(self.resolution.value)
        frames_count = duration_to_frames(self.duration.value.to(u.s).magnitude)

        hardware = _HARDWARE_CONFIGURATIONS[info["hardware"]]
        server_power = hardware["server_power"]
        server_embodied = hardware["server_embodied"]
        accelerator_embodied = hardware["accelerator_embodied"]
        server_accelerator_count = hardware["number_of_accelerators"]
        # Server power in the data is W; the DAG expects kW.
        server_accelerator_power = RangeValue(min=server_power["p2_5"] / 1000, max=server_power["p97_5"] / 1000)

        # GWP carbon intensity comes from the external_api's average_carbon_intensity calculated
        # attribute, so it shows up as an explicit, traceable node in the impacts graph. The raw mix
        # is still looked up here for the adpe/pe/wue factors, which feed water/resource outputs that
        # stay cached for a future Boavizta integration but are out of the current GWP scope.
        # datacenter_location is read here but NOT declared a direct logical dependency of impacts:
        # average_carbon_intensity already carries it as an ancestor, and it is a pure function of
        # provider (a declared dependency), so impacts is always correctly invalidated through them.
        mix_zone = self.external_api.datacenter_location.value
        if_electricity_mix = electricity_mixes.find_electricity_mix(zone=mix_zone)
        if if_electricity_mix is None:
            raise ValueError(f"Could not find electricity mix for `{mix_zone}` zone.")

        regression = dict(info["regression_parameters"])
        if self.with_audio.value:
            regression["non_audio_weight"] = 1.0

        impacts = compute_video_impacts_dag(
            video_width=width,
            video_height=height,
            video_frames_count=frames_count,
            request_latency=math.inf,
            server_accelerator_power=server_accelerator_power,
            if_electricity_mix_adpe=if_electricity_mix.adpe,
            if_electricity_mix_pe=if_electricity_mix.pe,
            if_electricity_mix_gwp=self.external_api.average_carbon_intensity.value.magnitude,
            if_electricity_mix_wue=if_electricity_mix.wue,
            datacenter_pue=self.external_api.data_center_pue.value.magnitude,
            datacenter_wue=datacenter_wue,
            accelerator_embodied_gwp=accelerator_embodied["gwp"],
            accelerator_embodied_adpe=accelerator_embodied["adpe"],
            accelerator_embodied_pe=accelerator_embodied["pe"],
            server_embodied_gwp=server_embodied["gwp"],
            server_embodied_adpe=server_embodied["adpe"],
            server_embodied_pe=server_embodied["pe"],
            server_accelerator_count=server_accelerator_count,
            **regression,
        )
        # The video DAG propagates RangeValue through nodes downstream of server_accelerator_power.
        # Collapse to scalar means so the impacts dict is JSON-serializable and downstream
        # ExplainableQuantity construction sees floats only.
        impacts = {key: mean_value_or_range(value) for key, value in impacts.items()}

        impacts_dict = ExplainableDict(
            impacts,
            f"Ecologits video impacts",
            left_parent=self.resolution,
            right_parent=self.duration,
            operator="compute impacts with EcoLogits compute_video_impacts_dag function"
            ).generate_explainable_object_with_logical_dependency(
            self.with_audio).generate_explainable_object_with_logical_dependency(
            self.external_api.data_center_pue).generate_explainable_object_with_logical_dependency(
            self.external_api.average_carbon_intensity).generate_explainable_object_with_logical_dependency(
            self.external_api.provider).generate_explainable_object_with_logical_dependency(
            self.external_api.model_name)
        impacts_dict.source = compute_video_impacts_dag_source
        self.impacts = impacts_dict


for attr_name in ecologits_video_calculated_attributes:
    setattr(EcoLogitsVideoGenExternalAPIJob, f"update_{attr_name}", create_update_method_for_ecologits_attribute(
        attr_name, ECOLOGITS_VIDEO_DEPENDENCY_GRAPH, video_dag, compute_video_impacts_dag_source))
