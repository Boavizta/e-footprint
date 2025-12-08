import math
from typing import Optional, Any

from ecologits.electricity_mix_repository import electricity_mixes
from ecologits.impacts.llm import compute_llm_impacts_dag
from ecologits.model_repository import models, ParametersMoE
from ecologits.tracers.utils import PROVIDER_CONFIG_MAP
from ecologits.utils.range_value import ValueOrRange, RangeValue


class EcoLogitsModel:
    def __str__(self):
        return f"EcoLogitsModel<{self.model.provider.name} - {self.model.name}>"

    def __init__(
            self,
            provider: str,
            model_name: str,
            output_token_count: int,
            request_latency: float | None = None,
            electricity_mix_zone: str | None = None,
    ):
        """
        High-level init to compute the impacts of an LLM generation request.

        Args:
            provider: Name of the provider.
            model_name: Name of the LLM used.
            output_token_count: Number of generated tokens.
            request_latency: Measured request latency in seconds.
            electricity_mix_zone: ISO 3166-1 alpha-3 code of the electricity mix zone (WOR by default).
        """
        self.model = models.find_model(provider=provider, model_name=model_name)
        if self.model is None:
            raise ValueError(f"Could not find model `{model_name}` for {provider} provider.")

        if isinstance(self.model.architecture.parameters, ParametersMoE):
            self.model_total_params = self.model.architecture.parameters.total
            self.model_active_params = self.model.architecture.parameters.active
        else:
            self.model_total_params = self.model.architecture.parameters
            self.model_active_params = self.model.architecture.parameters

        self.datacenter_location = PROVIDER_CONFIG_MAP[provider].datacenter_location
        self.datacenter_pue = PROVIDER_CONFIG_MAP[provider].datacenter_pue
        self.datacenter_wue = PROVIDER_CONFIG_MAP[provider].datacenter_wue

        self.electricity_mix_zone = electricity_mix_zone
        if self.electricity_mix_zone is None:
            self.electricity_mix_zone = self.datacenter_location
        if self.electricity_mix_zone is None:
            self.electricity_mix_zone = "WOR"
        if_electricity_mix = electricity_mixes.find_electricity_mix(zone=self.electricity_mix_zone)
        if if_electricity_mix is None:
            raise ValueError(f"Could not find electricity mix for `{self.electricity_mix_zone}` zone.")

        self.impacts = self.compute_llm_impacts(
            model_active_parameter_count=self.model_active_params,
            model_total_parameter_count=self.model_total_params,
            output_token_count=output_token_count,
            request_latency=request_latency,
            if_electricity_mix_adpe=if_electricity_mix.adpe,
            if_electricity_mix_pe=if_electricity_mix.pe,
            if_electricity_mix_gwp=if_electricity_mix.gwp,
            if_electricity_mix_wue=if_electricity_mix.wue,
            datacenter_pue=self.datacenter_pue,
            datacenter_wue=self.datacenter_wue,
        )

    @staticmethod
    def compute_llm_impacts(
            model_active_parameter_count: ValueOrRange,
            model_total_parameter_count: ValueOrRange,
            output_token_count: float,
            if_electricity_mix_adpe: float,
            if_electricity_mix_pe: float,
            if_electricity_mix_gwp: float,
            if_electricity_mix_wue: float,
            datacenter_pue: ValueOrRange,
            datacenter_wue: ValueOrRange,
            request_latency: Optional[float] = None,
            **kwargs: Any
    ) -> dict[str, float]:
        """
        Compute the impacts of an LLM generation request.
    
        Args:
            model_active_parameter_count: Number of active parameters of the model (in billion).
            model_total_parameter_count: Number of total parameters of the model (in billion).
            output_token_count: Number of generated tokens.
            if_electricity_mix_adpe: ADPe impact factor of electricity consumption of kgSbeq / kWh (Antimony).
            if_electricity_mix_pe: PE impact factor of electricity consumption in MJ / kWh.
            if_electricity_mix_gwp: GWP impact factor of electricity consumption in kgCO2eq / kWh.
            if_electricity_mix_wue: WCF impact factor of electricity consumption in L / kWh.
            datacenter_wue: Water Usage Effectiveness of the data center in L/kWh.
            datacenter_pue: Power Usage Effectiveness of the data center.
            request_latency: Measured request latency in seconds.
            **kwargs: Any other optional parameter.
        Returns:
            The impacts of an LLM generation request.
        """
        if request_latency is None:
            request_latency = math.inf
    
        active_params = model_active_parameter_count
        total_params = model_total_parameter_count
    
        if isinstance(model_active_parameter_count, RangeValue) or isinstance(model_total_parameter_count, RangeValue):
            if isinstance(model_active_parameter_count, RangeValue):
                active_params = (model_active_parameter_count.min + model_active_parameter_count.max) / 2
            if isinstance(model_total_parameter_count, RangeValue):
                total_params = (model_total_parameter_count.min + model_total_parameter_count.max) / 2

        return compute_llm_impacts_dag(
            model_active_parameter_count=active_params,
            model_total_parameter_count=total_params,
            output_token_count=output_token_count,
            request_latency=request_latency,
            if_electricity_mix_adpe=if_electricity_mix_adpe,
            if_electricity_mix_pe=if_electricity_mix_pe,
            if_electricity_mix_gwp=if_electricity_mix_gwp,
            if_electricity_mix_wue=if_electricity_mix_wue,
            datacenter_pue=datacenter_pue,
            datacenter_wue=datacenter_wue,
            **kwargs
        )
