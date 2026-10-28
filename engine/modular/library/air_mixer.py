"""
AirMixer Component Module.
Adiabatic Air Stream Mixer (Sum Node).
Blends multiple process air streams into a single homogeneous air stream,
strictly conserving total mass, oxygen content, and total enthalpy.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


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
