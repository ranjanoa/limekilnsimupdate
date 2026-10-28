"""
Stream Splitter.
Divides an incoming stream into two branches based on a defined split fraction.
"""

from typing import Dict, List, Any
import copy
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


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
