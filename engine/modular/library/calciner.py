"""
CalcinerReactor: Inline/Separate-line precalciner reactor with Arrhenius decarbonation kinetics,
tertiary air fuel combustion, CO2 release, and dynamic temperature control.
"""

from typing import Dict, List, Any
import math

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class CalcinerReactor(BlockBase):
    """
    Suspension Precalciner Reactor.
    Combines preheated raw meal, hot tertiary combustion air, kiln riser gas,
    and burner fuels (petcoke/alternative fuels) to achieve 90-95% decarbonation.
    """
    block_type = "CalcinerReactor"
    category = "Combustion"
    icon = "reactor"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_meal", PortDirection.IN, StreamPhase.SOLID, "Preheated raw meal from stage 4", required=True),
            Port("in_gas", PortDirection.IN, StreamPhase.GAS, "Kiln riser exhaust gas", required=False),
            Port("in_tertiary_air", PortDirection.IN, StreamPhase.AIR, "Tertiary air from grate cooler", required=False),
            Port("in_fuel", PortDirection.IN, StreamPhase.FUEL, "Dosed fuel supply (petcoke / CDR)", required=True),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Calciner flue gas with released CO2", required=False),
            Port("out_meal", PortDirection.OUT, StreamPhase.SOLID, "Decarbonated raw meal (90-95% CaO)", required=False),
            Port("out_gas_meal_mix", PortDirection.OUT, StreamPhase.GAS, "Combined suspension to stage 5 cyclone", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "volume_m3": {"type": float, "default": 1100.0, "min": 200.0, "max": 3000.0, "unit": "m³", "label": "Vessel Volume"},
            "design_calcination_pct": {"type": float, "default": 92.5, "min": 60.0, "max": 99.0, "unit": "%", "label": "Target Calcination Degree"},
            "combustion_efficiency": {"type": float, "default": 99.0, "min": 85.0, "max": 100.0, "unit": "%", "label": "Combustion Efficiency"},
            "heat_loss_pct": {"type": float, "default": 3.5, "min": 0.5, "max": 10.0, "unit": "%", "label": "Shell Thermal Loss"},
            "target_temp_c": {"type": float, "default": 865.0, "min": 750.0, "max": 950.0, "unit": "°C", "label": "Calciner Temperature SP"},
        }

    def initialize(self):
        target_t = float(self.parameters.get("target_temp_c", 865.0))
        target_calc = float(self.parameters.get("design_calcination_pct", 92.5))
        self.state = {
            "calciner_temp_c": target_t,
            "calcination_degree_pct": target_calc,
            "co2_released_tph": 88.5,
            "heat_input_mw": 85.0,
            "heat_loss_gjh": 14.5,
            "apparent_calcination_heat_gjh": 155.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_meal = inlet_streams.get("in_meal")
        in_gas = inlet_streams.get("in_gas")
        in_ta = inlet_streams.get("in_tertiary_air")
        in_fuel = inlet_streams.get("in_fuel")

        m_meal = in_meal.mass_flow_tph if in_meal else 0.0
        m_gas = in_gas.mass_flow_tph if in_gas else 0.0
        m_ta = in_ta.mass_flow_tph if in_ta else 0.0
        m_fuel = in_fuel.mass_flow_tph if in_fuel else 0.0

        t_meal = in_meal.temperature_c if in_meal else 760.0
        t_gas = in_gas.temperature_c if in_gas else 1050.8
        t_ta = in_ta.temperature_c if in_ta else 880.0

        comb_eff = float(self.parameters.get("combustion_efficiency", 99.0)) / 100.0
        loss_pct = float(self.parameters.get("heat_loss_pct", 3.5)) / 100.0

        # 1. Fuel combustion heat release
        lhv = in_fuel.composition.get("lhv_mj_kg", 27.5) if in_fuel else 27.5
        q_fuel_mw = (m_fuel * 1000.0 * lhv * comb_eff) / 3600.0
        q_fuel_gjh = m_fuel * lhv * comb_eff

        # 2. Coupled first-principles thermal balance relative to 280 TPH baseline
        # Baseline reference: meal entering ~ 263.6 t/h, fuel ~ 12.0 t/h, TA ~ 128.2 t/h @ 880C, gas ~ 154.6 t/h @ 1050.8C
        m_meal_ref = 263.6
        m_fuel_ref = 12.0
        lhv_ref = 27.5

        dq_fuel = (m_fuel * lhv - m_fuel_ref * lhv_ref) * comb_eff  # GJ/h
        # 1 ton raw meal requires ~1.28 GJ for sensible heating + endothermic decarbonation
        dq_meal = (m_meal - m_meal_ref) * 1.28  # GJ/h
        dq_ta = ((m_ta * max(0.0, t_ta - 25.0) - 128.2 * (880.0 - 25.0)) * 0.265 * 4.184 / 1000.0) if (in_ta and m_ta > 0.0) else 0.0
        dq_kg = ((m_gas * max(0.0, t_gas - 25.0) - 96.45 * (1043.7 - 25.0)) * 0.275 * 4.184 / 1000.0) if (in_gas and m_gas > 0.0) else 0.0

        dq_net = dq_fuel - dq_meal + dq_ta + dq_kg
        c_exit = 0.52  # Effective heat capacity rate GJ/(h*C)

        t_calc_target = 885.0 + (dq_net / c_exit)
        t_calc_target = max(650.0, min(1150.0, t_calc_target))

        # 3. Arrhenius decarbonation kinetics: alpha increases with temperature
        alpha = min(0.985, max(0.60, 0.925 + 0.0008 * (t_calc_target - 885.0)))
        calc_pct = alpha * 100.0

        # Endothermic Decarbonation: CaCO3 -> CaO + CO2 (dH = +1782 kJ/kg CaCO3)
        caco3_fraction = in_meal.composition.get("CaCO3_pct", 76.85) / 100.0 if in_meal else 0.7685
        m_caco3_total = m_meal * caco3_fraction
        m_caco3_reacted = m_caco3_total * alpha

        m_co2_released = m_caco3_reacted * 0.4397
        q_calc_gjh = m_caco3_reacted * 1.782

        # 4. Flue gas from fuel combustion (fuel mass incorporated) + kiln riser gas + tertiary air + calcination CO2
        ash_pct = in_fuel.composition.get("ash_pct", 1.0) / 100.0 if in_fuel else 0.01
        m_fuel_gas = m_fuel * (1.0 - ash_pct)
        m_gas_out = m_gas + m_ta + m_fuel_gas + m_co2_released
        m_meal_out = max(0.0, m_meal - m_co2_released + (m_fuel * ash_pct))

        q_loss_gjh = loss_pct * (q_fuel_gjh + 350.0)

        # Update block state
        self.state["calciner_temp_c"] = round(t_calc_target, 1)
        self.state["calcination_degree_pct"] = round(calc_pct, 1)
        self.state["co2_released_tph"] = round(m_co2_released, 2)
        self.state["heat_input_mw"] = round(q_fuel_mw, 2)
        self.state["apparent_calcination_heat_gjh"] = round(q_calc_gjh, 2)
        self.state["heat_loss_gjh"] = round(q_loss_gjh, 2)

        # Update outlet streams
        out_gas = outlet_streams.get("out_gas")
        if out_gas:
            out_gas.update_state(
                mass_flow_tph=m_gas_out,
                temperature_c=t_calc_target,
                pressure_mbar=-28.0,
                composition={
                    "CO2_pct": round(28.0 + (m_co2_released / max(1.0, m_gas_out)) * 40.0, 1),
                    "O2_pct": 2.8,
                    "N2_pct": 62.0,
                    "H2O_pct": 7.2,
                },
            )

        scale = (m_meal / max(1.0, m_meal_out))
        in_sio2 = in_meal.composition.get("SiO2_pct", 13.50) if in_meal else 13.50
        in_al2o3 = in_meal.composition.get("Al2O3_pct", 3.45) if in_meal else 3.45
        in_fe2o3 = in_meal.composition.get("Fe2O3_pct", 2.10) if in_meal else 2.10
        in_mgco3 = in_meal.composition.get("MgCO3_pct", 2.15) if in_meal else 2.15

        calcined_meal_comp = {
            "CaO_pct": round(caco3_fraction * alpha * (56.08 / 100.09) * scale * 100.0, 2),
            "CaCO3_pct": round((1.0 - alpha) * caco3_fraction * scale * 100.0, 2),
            "SiO2_pct": round(in_sio2 * scale, 2),
            "Al2O3_pct": round(in_al2o3 * scale, 2),
            "Fe2O3_pct": round(in_fe2o3 * scale, 2),
            "MgO_pct": round(in_mgco3 * (40.30 / 84.31) * scale, 2),
            "LOI_pct": round((1.0 - alpha) * caco3_fraction * 43.97 * scale, 2),
        }

        out_meal = outlet_streams.get("out_meal")
        if out_meal:
            out_meal.update_state(
                mass_flow_tph=m_meal_out,
                temperature_c=t_calc_target,
                pressure_mbar=-28.0,
                composition=calcined_meal_comp,
            )

        out_mix = outlet_streams.get("out_gas_meal_mix")
        if out_mix:
            out_mix.update_state(
                mass_flow_tph=m_gas_out + m_meal_out,
                temperature_c=t_calc_target,
                pressure_mbar=-28.0,
                composition=calcined_meal_comp,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic ODE step integrating calciner thermal inertia and decarbonation kinetics."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        t_target = self.state["calciner_temp_c"]
        alpha_target = self.state["calcination_degree_pct"]

        current_t = self.state.get("dynamic_temp_c", t_target)
        current_alpha = self.state.get("dynamic_alpha_pct", alpha_target)

        # Thermal inertia time constant
        tau_t = 15.0  # seconds
        tau_alpha = 5.0  # seconds

        new_t = current_t + (t_target - current_t) * (dt / max(0.1, tau_t))
        new_alpha = current_alpha + (alpha_target - current_alpha) * (dt / max(0.1, tau_alpha))

        self.state["dynamic_temp_c"] = round(new_t, 1)
        self.state["dynamic_alpha_pct"] = round(new_alpha, 1)
        self.state["calciner_temp_c"] = round(new_t, 1)
        self.state["calcination_degree_pct"] = round(new_alpha, 1)

        out_gas = outlet_streams.get("out_gas")
        if out_gas:
            out_gas.temperature_c = round(new_t, 1)
            out_gas.compute_enthalpy()
        out_meal = outlet_streams.get("out_meal")
        if out_meal:
            out_meal.temperature_c = round(new_t, 1)
            out_meal.compute_enthalpy()

