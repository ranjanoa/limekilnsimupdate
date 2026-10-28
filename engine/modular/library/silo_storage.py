"""
Storage silo or meal surge bin.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class SiloStorage(BlockBase):
    """
    Storage silo or meal surge bin.
    """
    block_type = "SiloStorage"
    category = "Feeding"
    icon = "database"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_solid", PortDirection.IN, StreamPhase.SOLID, "Inlet material from elevator", required=True),
            Port("out_solid", PortDirection.OUT, StreamPhase.SOLID, "Discharge to downstream process", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "capacity_tons": {"type": float, "default": 5000.0, "min": 100.0, "max": 50000.0, "unit": "t", "label": "Storage Capacity"},
            "initial_level_pct": {"type": float, "default": 65.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Initial Level"},
        }

    def initialize(self):
        cap = float(self.parameters.get("capacity_tons", 5000.0))
        lvl = float(self.parameters.get("initial_level_pct", 65.0))
        self.state = {
            "level_pct": lvl,
            "stored_tons": round(cap * lvl / 100.0, 1),
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_solid")
        out_stream = outlet_streams.get("out_solid")

        flow = in_stream.mass_flow_tph if in_stream else 0.0
        temp = in_stream.temperature_c if in_stream else 25.0
        comp = in_stream.composition if in_stream else {}

        if out_stream:
            out_stream.update_state(
                mass_flow_tph=flow,
                temperature_c=temp,
                pressure_mbar=0.0,
                composition=comp,
            )
        return outlet_streams
