"""
Multi-Input Boolean Logic Gate.
Evaluates boolean truth table operations across up to 3 binary inputs.
Supports AND, OR, XOR, NAND, NOR, NOT.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class LogicGate(BlockBase):
    """
    Multi-Input Boolean Logic Gate.
    Evaluates boolean truth table operations across up to 3 binary inputs.
    Supports AND, OR, XOR, NAND, NOR, NOT.
    """
    block_type = "LogicGate"
    category = "Control / Binary"
    icon = "🚪"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_a", PortDirection.IN, StreamPhase.BINARY, "Binary Input A", required=True),
            Port("in_b", PortDirection.IN, StreamPhase.BINARY, "Binary Input B", required=False),
            Port("in_c", PortDirection.IN, StreamPhase.BINARY, "Binary Input C (optional)", required=False),
            Port("out_q", PortDirection.OUT, StreamPhase.BINARY, "Logic Gate Output Q", required=True),
            Port("out_not_q", PortDirection.OUT, StreamPhase.BINARY, "Inverted Logic Output NOT Q", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "gate_type": {"type": str, "default": "AND", "label": "Gate Type (AND/OR/XOR/NAND/NOR/NOT)"},
        }

    def initialize(self):
        self.state = {
            "in_a": False,
            "in_b": False,
            "in_c": False,
            "output_q": False,
            "output_not_q": True,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_a = inlet_streams.get("in_a")
        in_b = inlet_streams.get("in_b")
        in_c = inlet_streams.get("in_c")
        out_q = outlet_streams.get("out_q")
        out_not_q = outlet_streams.get("out_not_q")

        a = in_a.binary_state if in_a else False
        b = in_b.binary_state if in_b else False
        c = in_c.binary_state if in_c else False
        gate = str(self.parameters.get("gate_type", "AND")).upper()

        if gate == "OR":
            q = a or b or (c if in_c else False)
        elif gate == "XOR":
            q = (a ^ b)
        elif gate == "NAND":
            q = not (a and (b if in_b else True) and (c if in_c else True))
        elif gate == "NOR":
            q = not (a or b or (c if in_c else False))
        elif gate == "NOT":
            q = not a
        else:
            # Default AND
            q = a and (b if in_b else True) and (c if in_c else True)

        not_q = not q

        self.state["in_a"] = a
        self.state["in_b"] = b
        self.state["in_c"] = c
        self.state["output_q"] = q
        self.state["output_not_q"] = not_q

        if out_q:
            out_q.update_state(binary_state=q, signal_value=1.0 if q else 0.0)
        if out_not_q:
            out_not_q.update_state(binary_state=not_q, signal_value=1.0 if not_q else 0.0)

        return outlet_streams
