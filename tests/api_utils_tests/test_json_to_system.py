import json
import os.path
from copy import deepcopy
from unittest.mock import patch

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system, compute_classes_generation_order
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_random_source_hourly_values
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.logger import logger
from tests import root_test_dir
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass


API_UTILS_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestJsonToSystem(IntegrationTestBaseClass):
    def setUp(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system.json"), "rb") as file:
            self.base_system_dict = json.load(file)

    def test_version_25_video_import_repairs_inputs_and_recomputes_old_cached_footprint(self):
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)

        _, objects, _ = json_to_system(self.base_system_dict)
        system = next(obj for obj in objects.values() if type(obj) is System)
        step = next(obj for obj in objects.values() if type(obj).__name__ == "UsageJourneyStep")
        api = EcoLogitsVideoGenExternalAPI("Video API", SourceObject("openai"), SourceObject("sora-2-pro"))
        job = EcoLogitsVideoGenExternalAPIJob.from_defaults(
            "Video job", external_api=api,
            resolution=SourceObject("1080p (1920 x 1080)", source=Sources.USER_DATA,
                                    confidence="high", comment="Original note"))
        step.jobs[job] = SourceValue(1 * u.dimensionless)
        old_total = system.total_footprint.value.sum()
        snapshots = [system_to_json(system, save_computed_state=mode) for mode in (False, True)]
        job.resolution = SourceObject("720p (1280 x 720)")
        expected_total = system.total_footprint.value.sum()
        self.assertNotEqual(old_total, expected_total)

        for snapshot, cached in zip(snapshots, (False, True)):
            with self.subTest(cached=cached):
                snapshot["efootprint_version"] = "25.0.0"
                snapshot["EcoLogitsVideoGenExternalAPIJob"][job.id]["resolution"]["value"] = "4K (3840 x 2160)"
                original_snapshot = deepcopy(snapshot)
                _, loaded, upgraded = json_to_system(snapshot)
                loaded_system, loaded_job = loaded[system.id], loaded[job.id]
                self.assertEqual(original_snapshot, snapshot)
                self.assertEqual("720p (1280 x 720)", loaded_job.resolution.value)
                self.assertIs(Sources.AUTOMATIC_REPLACEMENT, loaded_job.resolution.source)
                self.assertIsNone(loaded_job.resolution.confidence)
                self.assertTrue(loaded_job.resolution.comment.endswith("\n\nOriginal note"))
                self.assertEqual(api.id, loaded_job.external_api.id)
                self.assertFalse(type(loaded_system).total_footprint.slot(loaded_system).has_cached_value)
                if cached:
                    baseline = loaded_system.__dict__["_version_baseline"]
                    self.assertEqual("25.0.0", baseline["efootprint_version"])
                    self.assertEqual(old_total, baseline["values"][(system.id, "total_footprint", None)].value.sum())
                self.assertEqual(expected_total, loaded_system.total_footprint.value.sum())
                self.assertEqual("25.0.0", upgraded["efootprint_version"])
                round_trip = system_to_json(loaded_system, save_computed_state=cached)
                _, reloaded, _ = json_to_system(round_trip)
                self.assertEqual(loaded_job.resolution.to_json(), reloaded[job.id].resolution.to_json())
                self.assertEqual(expected_total, reloaded[system.id].total_footprint.value.sum())

    def test_current_version_video_import_skips_historical_resolution_migration(self):
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)

        api = EcoLogitsVideoGenExternalAPI("Video API", SourceObject("openai"), SourceObject("sora-2-pro"))
        job = EcoLogitsVideoGenExternalAPIJob.from_defaults(
            "Video job", external_api=api,
            resolution=SourceObject("1080p (1920 x 1080)", source=Sources.USER_DATA,
                                    confidence="high", comment="Keep authored choice"))
        snapshot = system_to_json(job, save_computed_state=False)
        self.assertEqual("27.0.0", snapshot["efootprint_version"])
        with patch.dict("efootprint.api_utils.version_upgrade_handlers.VERSION_UPGRADE_HANDLERS",
                        {25: lambda *_: self.fail("Current files must skip the historical handler")}):
            _, loaded, upgraded = json_to_system(snapshot)
        self.assertIs(snapshot, upgraded)
        self.assertEqual(job.resolution.to_json(), loaded[job.id].resolution.to_json())

    def test_version_26_file_with_stored_direct_ancestors_loads_and_saves_without_them(self):
        _, objects, _ = json_to_system(self.base_system_dict)
        system = next(obj for obj in objects.values() if type(obj) is System)
        system.total_footprint.value  # computed so the snapshot carries the stored total
        snapshot = system_to_json(system, save_computed_state=True)
        snapshot["efootprint_version"] = "26.0.1"
        snapshot["System"][system.id]["total_footprint"]["direct_ancestors_with_id"] = ["('x', 'y', None)"]

        _, loaded, _ = json_to_system(snapshot)
        round_trip = system_to_json(loaded[system.id], save_computed_state=True)

        self.assertNotIn("direct_ancestors_with_id", json.dumps(round_trip))
        self.assertEqual(system.total_footprint.value.sum(), loaded[system.id].total_footprint.value.sum())

    def test_automatic_replacement_source_reuses_singleton_after_both_snapshot_modes(self):
        """Test automatic source identity after inputs-only and cached snapshot loads."""
        from efootprint.abstract_modeling_classes.explainable_object_base_class import explainable_object_from_json
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)

        api = EcoLogitsVideoGenExternalAPI(
            "video api", SourceObject("openai", source=Sources.USER_DATA),
            SourceObject("sora-2-pro", source=Sources.HYPOTHESIS))
        job = EcoLogitsVideoGenExternalAPIJob.from_defaults(
            "video job", external_api=api,
            resolution=SourceObject("720p (1280 x 720)", source=Sources.AUTOMATIC_REPLACEMENT))

        for save_computed_state in (False, True):
            with self.subTest(save_computed_state=save_computed_state):
                snapshot = system_to_json(job, save_computed_state=save_computed_state)
                source_payload = snapshot["Sources"][Sources.AUTOMATIC_REPLACEMENT.id]
                self.assertEqual(
                    {"id": "automatic_replacement", "name": "automatic replacement", "link": None},
                    source_payload)
                _, loaded, _ = json_to_system(snapshot)
                loaded_api, loaded_job = loaded[api.id], loaded[job.id]
                self.assertIs(Sources.USER_DATA, loaded_api.provider.source)
                self.assertIs(Sources.HYPOTHESIS, loaded_api.model_name.source)
                self.assertIs(Sources.AUTOMATIC_REPLACEMENT, loaded_job.resolution.source)

        fallback = explainable_object_from_json(
            SourceObject("720p (1280 x 720)", source=Sources.AUTOMATIC_REPLACEMENT).to_json(), {})
        self.assertIs(Sources.AUTOMATIC_REPLACEMENT, fallback.source)

    def test_conditional_queries_use_registered_routes_after_both_snapshot_modes(self):
        """Test loaded video relationships support choice queries without registering instances."""
        from efootprint.abstract_modeling_classes.conditional_inputs import (
            allowed_values, dependent_inputs, resolve_input_path)
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)

        with patch("efootprint.abstract_modeling_classes.conditional_inputs.register_conditional_inputs",
                   side_effect=AssertionError("instance registration")):
            api = EcoLogitsVideoGenExternalAPI("video api", SourceObject("openai"), SourceObject("sora-2-pro"))
            job = EcoLogitsVideoGenExternalAPIJob.from_defaults("video job", external_api=api)
            job.request_duration
            for save_computed_state in (False, True):
                with self.subTest(save_computed_state=save_computed_state):
                    snapshot = system_to_json(job, save_computed_state=save_computed_state)
                    _, loaded, _ = json_to_system(snapshot)
                    loaded_job, loaded_api = loaded[job.id], loaded[api.id]
                    self.assertEqual({(loaded_job, "resolution")}, dependent_inputs({(loaded_api, "model_name")}))
                    self.assertEqual({(loaded_api, "model_name")}, dependent_inputs({(loaded_api, "provider")}))
                    self.assertEqual(
                        (loaded_api, "model_name"), resolve_input_path(loaded_job, "external_api.model_name"))
                    self.assertIn(
                        loaded_job.resolution, allowed_values(type(loaded_job), "resolution", loaded_api.model_name))
                    self.assertEqual(job.resolution, loaded_job.resolution)
                    self.assertEqual(api.model_name, loaded_api.model_name)

    def test_create_unlinked_server(self):
        full_dict = deepcopy(self.base_system_dict)
        with open(os.path.join(API_UTILS_TEST_DIR, "server_not_linked_to_usage_journey.json"), "rb") as file:
            full_dict["Server"].update(json.load(file))

        class_obj_dict, flat_obj_dict, _ = json_to_system(full_dict)

        self.assertEqual(2, len(list(class_obj_dict["Server"].values())))

    def test_conditional_edits_reject_and_rollback_after_both_snapshot_modes(self):
        """Test restored video inputs enforce conditional choices with and without serialized caches."""
        from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)

        api = EcoLogitsVideoGenExternalAPI("loaded video api", SourceObject("openai"), SourceObject("sora-2-pro"))
        job = EcoLogitsVideoGenExternalAPIJob.from_defaults("loaded video job", external_api=api)
        baseline_duration = job.request_duration.value
        api.use_footprint
        for save_computed_state in (False, True):
            with self.subTest(save_computed_state=save_computed_state):
                snapshot = system_to_json(job, save_computed_state=save_computed_state)
                _, loaded, _ = json_to_system(snapshot)
                loaded_job, loaded_api = loaded[job.id], loaded[api.id]
                server = loaded_api.server._value
                footprint_slot = type(server).use_footprint.slot(server)
                self.assertEqual(save_computed_state, footprint_slot.has_cached_value)
                original_link = loaded_job.external_api
                with self.assertRaisesRegex(ValueError, "resolution"):
                    ModelingUpdate([[loaded_api.provider, SourceObject("lightricks")],
                                    [loaded_api.model_name, SourceObject("ltx-2-t2v")]],
                                   eager_outputs=[(loaded_job, "request_duration")])
                self.assertEqual("openai", loaded_api.provider.value)
                self.assertEqual("sora-2-pro", loaded_api.model_name.value)
                self.assertEqual("720p (1280 x 720)", loaded_job.resolution.value)
                self.assertIs(original_link, loaded_job.external_api)
                self.assertIn(loaded_job, loaded_api.jobs)
                self.assertEqual(baseline_duration, loaded_job.request_duration.value)
                ModelingUpdate([[loaded_job.resolution, SourceObject("576p (1024 x 576)")],
                                [loaded_api.model_name, SourceObject("ltx-2-t2v")],
                                [loaded_api.provider, SourceObject("lightricks")]])
                self.assertFalse(footprint_slot.has_cached_value)
                _, reloaded, _ = json_to_system(system_to_json(loaded_job))
                self.assertEqual("576p (1024 x 576)", reloaded[job.id].resolution.value)
                self.assertEqual("ltx-2-t2v", reloaded[api.id].model_name.value)
                self.assertIs(reloaded[api.id], reloaded[job.id].external_api._value)

    def test_create_unlinked_uj(self):
        full_dict = deepcopy(self.base_system_dict)
        with open(os.path.join(API_UTILS_TEST_DIR, "uj_not_linked_to_usage_pattern.json"), "rb") as file:
            full_dict["UsageJourney"].update(json.load(file))

        class_obj_dict, flat_obj_dict, _ = json_to_system(full_dict)

    def test_serialized_system_with_uj_steps_as_list_relationships_loads_as_weight_one_dicts(self):
        from efootprint.abstract_modeling_classes.explainable_object_dict import WeightedExplainableObjectDict

        class_obj_dict, flat_obj_dict, _ = json_to_system(deepcopy(self.base_system_dict))

        usage_journey = list(class_obj_dict["UsageJourney"].values())[0]
        self.assertIsInstance(usage_journey.uj_steps, WeightedExplainableObjectDict)
        self.assertEqual(
            [1] * len(usage_journey.uj_steps), [weight.magnitude for weight in usage_journey.uj_steps.values()])
        for uj_step in usage_journey.uj_steps:
            self.assertIsInstance(uj_step.jobs, WeightedExplainableObjectDict)
            self.assertEqual([1] * len(uj_step.jobs), [weight.magnitude for weight in uj_step.jobs.values()])

    def test_update_value_after_system_creation(self):
        class_obj_dict, flat_obj_dict, _ = json_to_system(self.base_system_dict)

        list(class_obj_dict["Job"].values())[0].data_transferred = SourceValue(100 * u.GB, label="new value")

    def test_system_id_doesnt_change(self):
        class_obj_dict, flat_obj_dict, _ = json_to_system(self.base_system_dict)

        self.assertEqual(
            list(class_obj_dict["System"].values())[0].id, list(self.base_system_dict["System"].values())[0]["id"])

    def test_loads_when_usage_journey_step_has_no_jobs(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_no_jobs.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_9_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v9.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_10_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v10.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_11_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v11.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_12_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v12.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_13_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v13.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict, _ = json_to_system(base_system_dict)

    def test_loads_version_23_payload_with_plural_pattern_migration(self):
        fixture_path = os.path.join(API_UTILS_TEST_DIR, "base_system_v23.json")
        if not os.path.isfile(fixture_path):
            self.skipTest("big-system fixture not generated locally")

        with open(fixture_path, "rb") as file:
            version_23_system_dict = json.load(file)
        if version_23_system_dict["efootprint_version"] != "23.0.0":
            self.skipTest("big-system fixture is not version 23")

        _, _, upgraded_dict = json_to_system(version_23_system_dict)

        self.assertEqual("23.0.0", version_23_system_dict["efootprint_version"])
        self.assertTrue(all(
            "usage_journeys" in pattern and "hourly_occurrences" in pattern
            for pattern in upgraded_dict["UsagePattern"].values()))
        self.assertTrue(all(
            "edge_usage_journeys" in pattern and "hourly_deployment_starts" in pattern and "usage_span" in pattern
            for pattern in upgraded_dict["EdgeUsagePattern"].values()))
        self.assertTrue(all("usage_span" not in journey for journey in upgraded_dict["EdgeUsageJourney"].values()))

    def test_json_to_system_doesnt_update_input_dict(self):
        input_dict = deepcopy(self.base_system_dict)

        json_to_system(input_dict)

        self.assertDictEqual(input_dict, self.base_system_dict)

    def test_json_to_system_raises_clear_error_when_class_entry_is_not_an_object_dict(self):
        input_dict = deepcopy(self.base_system_dict)
        input_dict["Job"]["data_stored"] = {}

        with self.assertRaisesRegex(
                ValueError, r"Detected invalid data at `Job` level: \{\}. Only object dictionaries are valid at "
                            r"this level."):
            json_to_system(input_dict)

    def test_json_to_system_raises_clear_error_when_object_key_does_not_match_embedded_id(self):
        input_dict = deepcopy(self.base_system_dict)
        job_dict = next(iter(input_dict["Job"].values()))
        input_dict["Job"] = {"wrong_key": job_dict}

        with self.assertRaisesRegex(
                ValueError, r"Invalid JSON structure for `Job\.wrong_key`: embedded id is"):
            json_to_system(input_dict)

    def test_json_to_system_ignores_unrelated_top_level_keys(self):
        input_dict = deepcopy(self.base_system_dict)
        input_dict["custom_metadata"] = []

        class_obj_dict, flat_obj_dict, _ = json_to_system(input_dict)

        self.assertEqual(1, len(class_obj_dict["System"]))

    def test_json_to_system_raises_clear_error_for_legacy_class_corruption_before_upgrade(self):
        input_dict = {
            "efootprint_version": "15.0.0",
            "GenAIModel": {
                "model_1": {
                    "name": "Claude API server",
                    "id": "model_1",
                    "provider": {"value": "anthropic", "label": "provider"},
                    "model_name": {"value": "claude-sonnet-4-5", "label": "model"},
                    "server": "server_1",
                }
            },
            "GenAIJob": {
                "data_stored": {},
                "job_1": {
                    "name": "Code Review",
                    "id": "job_1",
                    "service": "model_1",
                    "output_token_count": SourceValue(2000 * u.dimensionless, label="tokens").to_json(),
                }
            },
        }

        with self.assertRaisesRegex(
                ValueError,
                r"Detected invalid data at `GenAIJob` level: \{\}. Only object dictionaries are valid at this level."):
            json_to_system(input_dict)

    def test_name_matching_another_objects_id_is_not_resolved_into_a_reference(self):
        # A scalar string attribute is treated as a reference when it equals an existing object id. `name` must be
        # exempt: otherwise an object whose name equals another object's id (e.g. a second "France" country loaded
        # after the catalog one keyed "France") gets its name silently turned into that Country, which later crashes
        # consumers that expect a string (e.g. the impact-repartition Sankey calling len(source.name)).
        full_dict = deepcopy(self.base_system_dict)
        original_country_id = next(iter(full_dict["Country"]))
        country_block = full_dict["Country"][original_country_id]
        # First country keyed "France" so its id collides with the name of the second country.
        first_country = deepcopy(country_block)
        first_country.update({"id": "France", "name": "France"})
        second_country = deepcopy(country_block)
        second_country.update({"id": "second-france", "name": "France"})
        full_dict["Country"] = {"France": first_country, "second-france": second_country}
        for usage_pattern in full_dict["UsagePattern"].values():
            if usage_pattern.get("country") == original_country_id:
                usage_pattern["country"] = "France"

        class_obj_dict, flat_obj_dict, _ = json_to_system(full_dict)

        self.assertEqual("France", class_obj_dict["Country"]["second-france"].name)
        self.assertIsInstance(class_obj_dict["Country"]["second-france"].name, str)

    def test_compute_object_generation_order(self):
        efootprint_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                   for modeling_object_class in ALL_EFOOTPRINT_CLASSES}
        classes_generation_order = compute_classes_generation_order(efootprint_classes_dict)

        self.assertListEqual(
            ["Device", "Country",
             "EdgeRAMComponent", "EdgeCPUComponent", "EdgeWorkloadComponent", "EdgeStorage",
             "EdgeComputerRAMComponent", "EdgeComputerCPUComponent", "EdgeApplianceComponent",
             "EdgeAppliance",
             "Network", "EcoLogitsGenAIExternalAPIServer", "EcoLogitsVideoGenExternalAPIServer", "Storage",
             "RecurrentEdgeStorageNeed", "EdgeDevice", "EdgeComputer",
             "BoaviztaCloudServer", "EcoLogitsGenAIExternalAPI", "EcoLogitsVideoGenExternalAPI",
             "RecurrentEdgeComponentNeed",
             "RecurrentEdgeProcessRAMNeed", "RecurrentEdgeProcessCPUNeed", "RecurrentEdgeProcessStorageNeed",
             "RecurrentEdgeWorkloadNeed", "RecurrentEdgeWorkload",
             "Server", "GPUServer", "EdgeDeviceGroup",
             "VideoStreaming", "Job", "GPUJob",
             "RecurrentEdgeDeviceNeed", "RecurrentEdgeProcess",
             "EcoLogitsGenAIExternalAPIJob", "EcoLogitsVideoGenExternalAPIJob", "VideoStreamingJob",
             "UsageJourneyStep", "RecurrentServerNeed", "UsageJourney", "EdgeFunction",
             "UsagePattern", "EdgeUsageJourney", "EdgeUsagePattern",
             "System"],
            classes_generation_order
        )

    def test_system_with_calculated_attr_loaded_from_unique_uj_without_uj_step_and_linked_to_up_doesnt_fail(self):
        uj = UsageJourney("Usage journey", uj_steps=[])
        up = UsagePattern(
            "usage pattern", usage_journeys=[uj], devices=[], network=Network.wifi_network(), country=Countries.FRANCE(),
            hourly_occurrences=create_random_source_hourly_values(timespan=1 * u.year))

        system = System("system", usage_patterns=[up], edge_usage_patterns=[])

        system_filepath = os.path.join(
            root_test_dir, "api_utils_tests", "unique_uj_without_uj_step_and_linked_to_up.json")
        system_to_json(system, output_filepath=system_filepath)

        with open(system_filepath, "r") as file:
            system_dict = json.load(file)

        logger.warning(f"Loading system from json")
        class_obj_dict, flat_obj_dict, _ = json_to_system(system_dict)
