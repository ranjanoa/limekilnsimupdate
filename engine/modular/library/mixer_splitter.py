"""
Mixer, Splitter, and Flow Conditioning Blocks:
- StreamMixer: Combines multiple streams adiabatically (conserves mass and enthalpy)
- StreamSplitter: Divides stream into multiple branches based on split ratio
- DamperValve: Throttles draft/flow with adjustable aperture and pressure drop
"""

from typing import Dict, List, Any
import copy

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class StreamMixer(BlockBase):
    """
    Adiabatic Stream Mixer.
    Blends multiple incoming material or gas streams into a single homogenous stream,
    strictly conserving total mass and total enthalpy.
    """
    block_type = "StreamMixer"
    category = "Flow Control"
    icon = "git-merge"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_1", PortDirection.IN, StreamPhase.SOLID, "First inlet stream", required=True),
            Port("in_2", PortDirection.IN, StreamPhase.SOLID, "Second inlet stream", required=False),
            Port("in_3", PortDirection.IN, StreamPhase.SOLID, "Third inlet stream", required=False),
            Port("out_mixed", PortDirection.OUT, StreamPhase.SOLID, "Blended mixed discharge stream", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "pressure_mode": {"type": str, "default": "minimum", "label": "Outlet Pressure Mode"},
        }

    def initialize(self):
        self.state = {
            "mixed_mass_tph": 0.0,
            "mixed_temp_c": 25.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        active_inlets = [s for s in inlet_streams.values() if s is not None and s.mass_flow_tph > 0.0]
        out_stream = outlet_streams.get("out_mixed")

        if not active_inlets:
            if out_stream:
                out_stream.update_state(mass_flow_tph=0.0, temperature_c=25.0)
            return outlet_streams

        total_mass = sum(s.mass_flow_tph for s in active_inlets)
        total_enthalpy = sum(s.enthalpy_gjh for s in active_inlets)

        # Weighted temperature
        sum_c_t = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() * s.temperature_c for s in active_inlets)
        sum_c = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() for s in active_inlets)
        t_mixed = (sum_c_t / sum_c) if sum_c > 0.0 else 25.0

        p_mixed = min(s.pressure_mbar for s in active_inlets)

        # Combined composition
        blended_comp: Dict[str, float] = {}
        for s in active_inlets:
            w = s.mass_flow_tph / total_mass
            for comp_key, val in s.composition.items():
                if isinstance(val, (int, float)):
                    blended_comp[comp_key] = blended_comp.get(comp_key, 0.0) + val * w

        self.state["mixed_mass_tph"] = round(total_mass, 2)
        self.state["mixed_temp_c"] = round(t_mixed, 1)

        if out_stream:
            out_stream.phase = active_inlets[0].phase
            out_stream.update_state(
                mass_flow_tph=total_mass,
                temperature_c=t_mixed,
                pressure_mbar=p_mixed,
                composition=blended_comp,
            )

        return outlet_streams


class StreamSplitter(BlockBase):
    """
    Stream Splitter.
    Divides an incoming stream into two branches based on a defined split fraction.
    """
    block_type = "StreamSplitter"
    category = "Flow Control"
    icon = "git-branch"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_stream", PortDirection.IN, StreamPhase.SOLID, "Input stream to split", required=True),
            Port("out_1", PortDirection.OUT, StreamPhase.SOLID, "Branch 1 output", required=True),
            Port("out_2", PortDirection.OUT, StreamPhase.SOLID, "Branch 2 output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "split_fraction": {"type": float, "default": 0.5, "min": 0.0, "max": 1.0, "unit": "-", "label": "Split Ratio to Branch 1 (0 to 1)"},
        }

    def initialize(self):
        self.state = {
            "branch_1_mass_tph": 0.0,
            "branch_2_mass_tph": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_stream")
        out_1 = outlet_streams.get("out_1")
        out_2 = outlet_streams.get("out_2")

        if not in_stream or in_stream.mass_flow_tph <= 0.0:
            if out_1:
                out_1.update_state(mass_flow_tph=0.0)
            if out_2:
                out_2.update_state(mass_flow_tph=0.0)
            return outlet_streams

        frac = float(self.parameters.get("split_fraction", 0.5))
        m_total = in_stream.mass_flow_tph
        m_1 = m_total * frac
        m_2 = m_total * (1.0 - frac)

        self.state["branch_1_mass_tph"] = round(m_1, 2)
        self.state["branch_2_mass_tph"] = round(m_2, 2)

        if out_1:
            out_1.phase = in_stream.phase
            out_1.update_state(
                mass_flow_tph=m_1,
                temperature_c=in_stream.temperature_c,
                pressure_mbar=in_stream.pressure_mbar,
                composition=copy.deepcopy(in_stream.composition),
            )

        if out_2:
            out_2.phase = in_stream.phase
            out_2.update_state(
                mass_flow_tph=m_2,
                temperature_c=in_stream.temperature_c,
                pressure_mbar=in_stream.pressure_mbar,
                composition=copy.deepcopy(in_stream.composition),
            )

        return outlet_streams


class DamperValve(BlockBase):
    """
    Process Damper / Control Valve.
    Modulates gas draft and flow restriction.
    """
    block_type = "DamperValve"
    category = "Flow Control"
    icon = "sliders"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_stream", PortDirection.IN, StreamPhase.GAS, "Upstream duct/pipe", required=True),
            Port("out_stream", PortDirection.OUT, StreamPhase.GAS, "Downstream throttled duct", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "opening_pct": {"type": float, "default": 80.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Damper Opening"},
            "dp_nominal_mbar": {"type": float, "default": 2.0, "min": 0.1, "max": 20.0, "unit": "mbar", "label": "Nominal Pressure Drop"},
        }

    def initialize(self):
        self.state = {
            "actual_dp_mbar": 2.0,
            "opening_pct": 80.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_stream")
        out_stream = outlet_streams.get("out_stream")

        if not in_stream:
            return outlet_streams

        opening = max(1.0, float(self.parameters.get("opening_pct", 80.0))) / 100.0
        dp_nom = float(self.parameters.get("dp_nominal_mbar", 2.0))
        actual_dp = dp_nom / (opening ** 2)

        self.state["actual_dp_mbar"] = round(actual_dp, 2)
        self.state["opening_pct"] = round(opening * 100.0, 1)

        if out_stream:
            out_stream.phase = in_stream.phase
            out_stream.update_state(
                mass_flow_tph=in_stream.mass_flow_tph,
                temperature_c=in_stream.temperature_c,
                pressure_mbar=in_stream.pressure_mbar - actual_dp,
                composition=copy.deepcopy(in_stream.composition),
            )

        return outlet_streams


class FuelMixer(BlockBase):
    """
    Multi-Fuel Summing & Blending Station (Fuel Sum Node).
    Sums multiple fuel supplies (e.g. Coal/Petcoke Feeder + RDF Alternative Fuel Feeder + Biomass Feeder)
    into a single homogenized fuel stream for delivery to the Calciner or Rotary Kiln / Lime Kiln.
    Strictly calculates total fuel flow (t/h), weighted Lower Heating Value (LHV, MJ/kg),
    ash content (%), moisture (%), total thermal power (MW / GJ/h), and Thermal Substitution Rate (TSR %).
    """
    block_type = "FuelMixer"
    category = "Combustion"
    icon = "flame"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_fuel_1", PortDirection.IN, StreamPhase.FUEL, "Primary fuel supply (e.g. Coal / Petcoke)", required=True),
            Port("in_fuel_2", PortDirection.IN, StreamPhase.FUEL, "Secondary fuel supply (e.g. RDF / Alternative Fuel)", required=False),
            Port("in_fuel_3", PortDirection.IN, StreamPhase.FUEL, "Tertiary fuel supply (e.g. Biomass / Liquid waste)", required=False),
            Port("in_fuel_4", PortDirection.IN, StreamPhase.FUEL, "Supplementary fuel supply", required=False),
            Port("out_fuel", PortDirection.OUT, StreamPhase.FUEL, "Blended mixed fuel discharge to calciner/burner", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "blending_mode": {"type": str, "default": "adiabatic", "label": "Blending Mode"},
            "heat_loss_pct": {"type": float, "default": 0.0, "min": 0.0, "max": 5.0, "unit": "%", "label": "Thermal Loss"},
        }

    def initialize(self):
        self.state = {
            "total_fuel_rate_tph": 0.0,
            "blended_lhv_mj_kg": 0.0,
            "total_heat_input_mw": 0.0,
            "total_heat_input_gjh": 0.0,
            "blended_ash_pct": 0.0,
            "blended_moisture_pct": 0.0,
            "rdf_alt_fuel_share_pct": 0.0,
            "primary_fuel_share_pct": 100.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream] = None,
    ) -> Dict[str, ProcessStream]:
        if outlet_streams is None:
            outlet_streams = {}
        if "out_fuel" not in outlet_streams:
            outlet_streams["out_fuel"] = ProcessStream(
                stream_id=0,
                name=f"{self.block_id}_Blended_Fuel",
                phase=StreamPhase.FUEL,
                mass_flow_tph=0.0,
                temperature_c=25.0,
            )

        active_inlets = [(k, s) for k, s in inlet_streams.items() if s is not None and s.mass_flow_tph > 0.0]
        out_stream = outlet_streams.get("out_fuel")

        if not active_inlets:
            self.state["total_fuel_rate_tph"] = 0.0
            self.state["blended_lhv_mj_kg"] = 0.0
            self.state["total_heat_input_mw"] = 0.0
            self.state["total_heat_input_gjh"] = 0.0
            self.state["rdf_alt_fuel_share_pct"] = 0.0
            if out_stream:
                out_stream.update_state(mass_flow_tph=0.0, temperature_c=25.0)
            return outlet_streams

        total_mass = sum(s.mass_flow_tph for _, s in active_inlets)

        # Weighted LHV, Ash, and Moisture
        total_energy_gjh = 0.0
        sum_ash = 0.0
        sum_moist = 0.0
        alt_energy_gjh = 0.0

        for port_name, s in active_inlets:
            lhv = s.composition.get("lhv_mj_kg", 28.0)
            ash = s.composition.get("ash_pct", 1.0)
            moist = s.composition.get("moisture_pct", 1.0)
            energy = s.mass_flow_tph * lhv

            total_energy_gjh += energy
            sum_ash += s.mass_flow_tph * ash
            sum_moist += s.mass_flow_tph * moist

            # Check if alternative fuel (RDF, Biomass, or from in_fuel_2 / in_fuel_3 / in_fuel_4)
            name_lower = (s.name or "").lower()
            fuel_name_lower = str(s.composition.get("fuel_name", "")).lower()
            to_port = getattr(s, "to_port", "") or ""
            is_alt = (
                "rdf" in name_lower or "alt" in name_lower or "bio" in name_lower
                or "rdf" in fuel_name_lower or "alt" in fuel_name_lower
                or port_name in ["in_fuel_2", "in_fuel_3", "in_fuel_4"]
                or to_port in ["in_fuel_2", "in_fuel_3", "in_fuel_4"]
            )
            if is_alt and port_name != "in_fuel_1" and to_port != "in_fuel_1":
                alt_energy_gjh += energy

        blended_lhv = (total_energy_gjh / total_mass) if total_mass > 0.0 else 0.0
        blended_ash = (sum_ash / total_mass) if total_mass > 0.0 else 0.0
        blended_moist = (sum_moist / total_mass) if total_mass > 0.0 else 0.0

        heat_mw = (total_energy_gjh * 1000.0) / 3600.0
        tsr_pct = (alt_energy_gjh / total_energy_gjh * 100.0) if total_energy_gjh > 0.0 else 0.0

        # Weighted temperature
        sum_c_t = sum(s.mass_flow_tph * s.temperature_c for _, s in active_inlets)
        t_mixed = (sum_c_t / total_mass) if total_mass > 0.0 else 25.0

        self.state["total_fuel_rate_tph"] = round(total_mass, 2)
        self.state["blended_lhv_mj_kg"] = round(blended_lhv, 2)
        self.state["total_heat_input_mw"] = round(heat_mw, 2)
        self.state["total_heat_input_gjh"] = round(total_energy_gjh, 2)
        self.state["blended_ash_pct"] = round(blended_ash, 2)
        self.state["blended_moisture_pct"] = round(blended_moist, 2)
        self.state["rdf_alt_fuel_share_pct"] = round(tsr_pct, 1)
        self.state["primary_fuel_share_pct"] = round(100.0 - tsr_pct, 1)

        if out_stream:
            out_stream.phase = StreamPhase.FUEL
            out_stream.update_state(
                mass_flow_tph=round(total_mass, 3),
                temperature_c=round(t_mixed, 1),
                pressure_mbar=0.0,
                composition={
                    "fuel_name": f"Blended Fuel (TSR {round(tsr_pct, 1)}%)",
                    "lhv_mj_kg": round(blended_lhv, 2),
                    "ash_pct": round(blended_ash, 2),
                    "moisture_pct": round(blended_moist, 2),
                    "tsr_pct": round(tsr_pct, 1),
                },
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        self.evaluate_steady_state(inlet_streams, outlet_streams)


class AirMixer(BlockBase):
    """
    Adiabatic Air Stream Mixer (Sum Node).
    Blends multiple process air streams (e.g. Tertiary Air, Secondary Air, Ambient Cooling Air, False Air Leakage)
    into a single homogeneous air stream, strictly conserving total mass, oxygen content, and total enthalpy.
    """
    block_type = "AirMixer"
    category = "Flow Control"
    icon = "wind"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_air_1", PortDirection.IN, StreamPhase.AIR, "Primary air inlet", required=True),
            Port("in_air_2", PortDirection.IN, StreamPhase.AIR, "Secondary air / dilution air", required=False),
            Port("in_air_3", PortDirection.IN, StreamPhase.AIR, "Tertiary air / false air inlet", required=False),
            Port("in_air_4", PortDirection.IN, StreamPhase.AIR, "Auxiliary air inlet", required=False),
            Port("out_air", PortDirection.OUT, StreamPhase.AIR, "Combined air stream discharge", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "pressure_mode": {"type": str, "default": "minimum", "label": "Discharge Pressure Mode"},
        }

    def initialize(self):
        self.state = {
            "total_air_tph": 0.0,
            "blended_temp_c": 25.0,
            "total_volume_nm3h": 0.0,
            "total_enthalpy_gjh": 0.0,
            "blended_o2_pct": 20.9,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream] = None,
    ) -> Dict[str, ProcessStream]:
        if outlet_streams is None:
            outlet_streams = {}
        if "out_air" not in outlet_streams:
            outlet_streams["out_air"] = ProcessStream(
                stream_id=0,
                name=f"{self.block_id}_Blended_Air",
                phase=StreamPhase.AIR,
                mass_flow_tph=0.0,
                temperature_c=25.0,
            )

        active_inlets = [s for s in inlet_streams.values() if s is not None and s.mass_flow_tph > 0.0]
        out_stream = outlet_streams.get("out_air")

        if not active_inlets:
            self.state["total_air_tph"] = 0.0
            self.state["blended_temp_c"] = 25.0
            self.state["total_volume_nm3h"] = 0.0
            self.state["total_enthalpy_gjh"] = 0.0
            self.state["blended_o2_pct"] = 20.9
            if out_stream:
                out_stream.update_state(mass_flow_tph=0.0, temperature_c=25.0)
            return outlet_streams

        total_mass = sum(s.mass_flow_tph for s in active_inlets)
        total_enthalpy = sum(s.enthalpy_gjh for s in active_inlets)

        # Weighted temperature by mass * Cp
        sum_c_t = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() * s.temperature_c for s in active_inlets)
        sum_c = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() for s in active_inlets)
        t_mixed = (sum_c_t / sum_c) if sum_c > 0.0 else 25.0

        p_mixed = min(s.pressure_mbar for s in active_inlets)

        # Weighted O2 and species
        blended_comp: Dict[str, float] = {}
        for s in active_inlets:
            w = s.mass_flow_tph / total_mass
            comp = s.composition or {"O2_pct": 20.9, "N2_pct": 79.1}
            for comp_key, val in comp.items():
                if isinstance(val, (int, float)):
                    blended_comp[comp_key] = blended_comp.get(comp_key, 0.0) + val * w

        vol_nm3h = (total_mass * 1000.0) / 1.293  # Standard air density 1.293 kg/Nm3
        o2_pct = blended_comp.get("O2_pct", 20.9)

        self.state["total_air_tph"] = round(total_mass, 2)
        self.state["blended_temp_c"] = round(t_mixed, 1)
        self.state["total_volume_nm3h"] = round(vol_nm3h, 1)
        self.state["total_enthalpy_gjh"] = round(total_enthalpy, 2)
        self.state["blended_o2_pct"] = round(o2_pct, 2)

        if out_stream:
            out_stream.phase = StreamPhase.AIR
            out_stream.update_state(
                mass_flow_tph=round(total_mass, 3),
                temperature_c=round(t_mixed, 1),
                pressure_mbar=p_mixed,
                composition=blended_comp,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        self.evaluate_steady_state(inlet_streams, outlet_streams)


class GasMixer(BlockBase):
    """
    Adiabatic Hot Gas & Flue Gas Mixer (Sum Node).
    Blends multiple process gas streams (e.g. Kiln Exhaust Gas, Calciner Exhaust, Cooler Vent Gas, Hot Gas Generator, Infiltration Leakage)
    into a single homogeneous gas stream with rigorous conservation of mass, thermal enthalpy, species composition (CO2%, O2%, N2%, H2O%),
    and dust loading.
    """
    block_type = "GasMixer"
    category = "Flow Control"
    icon = "cloud"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_gas_1", PortDirection.IN, StreamPhase.GAS, "Primary hot gas inlet", required=True),
            Port("in_gas_2", PortDirection.IN, StreamPhase.GAS, "Secondary gas inlet / bypass", required=False),
            Port("in_gas_3", PortDirection.IN, StreamPhase.GAS, "Tertiary gas inlet / leak", required=False),
            Port("in_gas_4", PortDirection.IN, StreamPhase.GAS, "Auxiliary gas inlet", required=False),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Combined hot flue gas discharge", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "pressure_mode": {"type": str, "default": "minimum", "label": "Discharge Pressure Mode"},
        }

    def initialize(self):
        self.state = {
            "total_gas_tph": 0.0,
            "blended_temp_c": 25.0,
            "total_volume_nm3h": 0.0,
            "total_enthalpy_gjh": 0.0,
            "blended_co2_pct": 0.0,
            "blended_o2_pct": 0.0,
            "blended_dust_gm3": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream] = None,
    ) -> Dict[str, ProcessStream]:
        if outlet_streams is None:
            outlet_streams = {}
        if "out_gas" not in outlet_streams:
            outlet_streams["out_gas"] = ProcessStream(
                stream_id=0,
                name=f"{self.block_id}_Blended_Gas",
                phase=StreamPhase.GAS,
                mass_flow_tph=0.0,
                temperature_c=25.0,
            )

        active_inlets = [s for s in inlet_streams.values() if s is not None and s.mass_flow_tph > 0.0]
        out_stream = outlet_streams.get("out_gas")

        if not active_inlets:
            self.state["total_gas_tph"] = 0.0
            self.state["blended_temp_c"] = 25.0
            self.state["total_volume_nm3h"] = 0.0
            self.state["total_enthalpy_gjh"] = 0.0
            self.state["blended_co2_pct"] = 0.0
            self.state["blended_o2_pct"] = 0.0
            self.state["blended_dust_gm3"] = 0.0
            if out_stream:
                out_stream.update_state(mass_flow_tph=0.0, temperature_c=25.0)
            return outlet_streams

        total_mass = sum(s.mass_flow_tph for s in active_inlets)
        total_enthalpy = sum(s.enthalpy_gjh for s in active_inlets)

        # Weighted temperature by mass * Cp
        sum_c_t = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() * s.temperature_c for s in active_inlets)
        sum_c = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() for s in active_inlets)
        t_mixed = (sum_c_t / sum_c) if sum_c > 0.0 else 25.0

        p_mixed = min(s.pressure_mbar for s in active_inlets)

        # Weighted species composition
        blended_comp: Dict[str, float] = {}
        for s in active_inlets:
            w = s.mass_flow_tph / total_mass
            comp = s.composition or {"CO2_pct": 20.0, "O2_pct": 3.0, "N2_pct": 70.0, "H2O_pct": 7.0}
            for comp_key, val in comp.items():
                if isinstance(val, (int, float)):
                    blended_comp[comp_key] = blended_comp.get(comp_key, 0.0) + val * w

        # Flue gas density ~1.34 kg/Nm3
        vol_nm3h = (total_mass * 1000.0) / 1.34
        co2_pct = blended_comp.get("CO2_pct", 0.0)
        o2_pct = blended_comp.get("O2_pct", 0.0)
        dust = blended_comp.get("dust_concentration_g_nm3", 0.0)

        self.state["total_gas_tph"] = round(total_mass, 2)
        self.state["blended_temp_c"] = round(t_mixed, 1)
        self.state["total_volume_nm3h"] = round(vol_nm3h, 1)
        self.state["total_enthalpy_gjh"] = round(total_enthalpy, 2)
        self.state["blended_co2_pct"] = round(co2_pct, 2)
        self.state["blended_o2_pct"] = round(o2_pct, 2)
        self.state["blended_dust_gm3"] = round(dust, 2)

        if out_stream:
            out_stream.phase = StreamPhase.GAS
            out_stream.update_state(
                mass_flow_tph=round(total_mass, 3),
                temperature_c=round(t_mixed, 1),
                pressure_mbar=p_mixed,
                composition=blended_comp,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        self.evaluate_steady_state(inlet_streams, outlet_streams)


