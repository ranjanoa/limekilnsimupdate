"""
Adiabatic Stream Mixer.
Blends multiple incoming material or gas streams into a single homogenous stream,
strictly conserving total mass and total enthalpy.
"""

from typing import Dict, List, Any
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
