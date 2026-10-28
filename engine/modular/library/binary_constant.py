"""
Binary / Discrete Constant Source Block.
Provides a fixed or configurable digital state (True or False) and its inversion.
Used for static safety permissives, run commands, interlock overrides, or digital stimuli.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class BinaryConstant(BlockBase):
    """
    Binary / Discrete Constant Source Block.
    Provides a fixed or configurable digital state (True or False) and its inversion.
    Used for static safety permissives, run commands, interlock overrides, or digital stimuli.
    """
    block_type = "BinaryConstant"
    category = "Control / Binary"
    icon = "🔘"

    def _define_ports(self) -> List[Port]:
        return [
            Port("out_state", PortDirection.OUT, StreamPhase.BINARY, "Constant digital state output", required=True),
            Port("out_not_state", PortDirection.OUT, StreamPhase.BINARY, "Inverted binary state output (NOT)", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "constant_state": {"type": bool, "default": True, "label": "Constant State (True=High, False=Low)"},
            "description": {"type": str, "default": "Digital Constant", "label": "Tag Description"},
        }

    def initialize(self):
        st = bool(self.parameters.get("constant_state", True))
        self.state = {
            "constant_state": st,
            "output_state": st,
            "output_not_state": not st,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        st = bool(self.parameters.get("constant_state", True))
        out_s = outlet_streams.get("out_state")
        out_not = outlet_streams.get("out_not_state")

        self.state["constant_state"] = st
        self.state["output_state"] = st
        self.state["output_not_state"] = not st

        if out_s:
            out_s.update_state(binary_state=st, signal_value=1.0 if st else 0.0)
        if out_not:
            out_not.update_state(binary_state=not st, signal_value=0.0 if st else 1.0)
        return outlet_streams
