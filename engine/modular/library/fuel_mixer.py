"""
Multi-Fuel Summing & Blending Station (Fuel Sum Node).
Sums multiple fuel supplies (e.g. Coal/Petcoke Feeder + RDF Alternative Fuel Feeder + Biomass Feeder)
into a single homogenized fuel stream for delivery to the Calciner or Rotary Kiln / Lime Kiln.
Strictly calculates total fuel flow (t/h), weighted Lower Heating Value (LHV, MJ/kg),
ash content (%), moisture (%), total thermal power (MW / GJ/h), and Thermal Substitution Rate (TSR %).
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


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
