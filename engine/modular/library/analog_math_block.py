"""
Analog Math & Linear Scaling Operator Block.
Performs arithmetic operations (Y = Gain * (A op B) + Offset).
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogMathBlock(BlockBase):
    """
    Analog Math & Linear Scaling Operator Block.
    Performs arithmetic operations (Y = Gain * (A op B) + Offset).
    """
    block_type = "AnalogMathBlock"
    category = "Control / Analog"
    icon = "🧮"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_a", PortDirection.IN, StreamPhase.SIGNAL, "Primary Signal A", required=True),
            Port("in_b", PortDirection.IN, StreamPhase.SIGNAL, "Secondary Signal B (optional)", required=False),
            Port("out_val", PortDirection.OUT, StreamPhase.SIGNAL, "Math output result", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "operation": {"type": str, "default": "SCALE_OFFSET", "label": "Math Operation (ADD/SUBTRACT/MULTIPLY/DIVIDE/SCALE_OFFSET)"},
            "gain": {"type": float, "default": 1.0, "label": "Multiplier Gain"},
            "offset": {"type": float, "default": 0.0, "label": "Bias / Offset"},
        }

    def initialize(self):
        self.state = {
            "in_a": 0.0,
            "in_b": 0.0,
            "result": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_a = inlet_streams.get("in_a")
        in_b = inlet_streams.get("in_b")
        out_s = outlet_streams.get("out_val")

        a = in_a.signal_value if in_a else 0.0
        b = in_b.signal_value if in_b else 0.0
        gain = float(self.parameters.get("gain", 1.0))
        offset = float(self.parameters.get("offset", 0.0))
        op = str(self.parameters.get("operation", "SCALE_OFFSET")).upper()

        if op == "ADD":
            res = gain * (a + b) + offset
        elif op == "SUBTRACT":
            res = gain * (a - b) + offset
        elif op == "MULTIPLY":
            res = gain * (a * b) + offset
        elif op == "DIVIDE":
            res = gain * (a / max(1e-6, b)) + offset
        else:
            # SCALE_OFFSET: Y = Gain * A + Offset
            res = gain * a + offset

        self.state["in_a"] = round(a, 2)
        self.state["in_b"] = round(b, 2)
        self.state["result"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
