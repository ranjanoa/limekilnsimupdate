"""
Bistable RS (Set-Reset) Memory Latch.
Maintains latch state across simulation steps.
Used for safety trip latches, manual lockout acknowledgment, and motor start/stop circuits.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class RSFlipFlop(BlockBase):
    """
    Bistable RS (Set-Reset) Memory Latch.
    Maintains latch state across simulation steps.
    Used for safety trip latches, manual lockout acknowledgment, and motor start/stop circuits.
    """
    block_type = "RSFlipFlop"
    category = "Control / Binary"
    icon = "🔲"

    def _define_ports(self) -> List[Port]:
        return [
            Port("set", PortDirection.IN, StreamPhase.BINARY, "Set Trigger (S)", required=True),
            Port("reset", PortDirection.IN, StreamPhase.BINARY, "Reset Trigger (R)", required=True),
            Port("out_q", PortDirection.OUT, StreamPhase.BINARY, "Latch State Output Q", required=True),
            Port("out_not_q", PortDirection.OUT, StreamPhase.BINARY, "Inverted State Output NOT Q", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "priority": {"type": str, "default": "RESET_DOMINANT", "label": "Priority Mode (RESET_DOMINANT/SET_DOMINANT)"},
            "initial_state": {"type": bool, "default": False, "label": "Initial Power-On State"},
        }

    def initialize(self):
        init_st = bool(self.parameters.get("initial_state", False))
        self.q = init_st
        self.state = {
            "set_active": False,
            "reset_active": False,
            "latch_q": init_st,
            "latch_not_q": not init_st,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("set")
        in_r = inlet_streams.get("reset")
        out_q = outlet_streams.get("out_q")
        out_not_q = outlet_streams.get("out_not_q")

        s = in_s.binary_state if in_s else False
        r = in_r.binary_state if in_r else False
        prio = str(self.parameters.get("priority", "RESET_DOMINANT")).upper()

        if prio == "SET_DOMINANT":
            if s:
                self.q = True
            elif r:
                self.q = False
        else:
            # RESET_DOMINANT
            if r:
                self.q = False
            elif s:
                self.q = True

        not_q = not self.q
        self.state["set_active"] = s
        self.state["reset_active"] = r
        self.state["latch_q"] = self.q
        self.state["latch_not_q"] = not_q

        if out_q:
            out_q.update_state(binary_state=self.q, signal_value=1.0 if self.q else 0.0)
        if out_not_q:
            out_not_q.update_state(binary_state=not_q, signal_value=1.0 if not_q else 0.0)

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        self.evaluate_steady_state(inlet_streams, outlet_streams)
