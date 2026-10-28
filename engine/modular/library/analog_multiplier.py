"""
Analog Multiplier & Ratio Divider Block.
Computes product / ratio across inputs:
Output = gain * (in_a * in_b / in_div) + bias
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogMultiplier(BlockBase):
    """
    Analog Multiplier & Ratio Divider Block.
    Computes product / ratio across inputs:
    Output = gain * (in_a * in_b / in_div) + bias
    """
    block_type = "AnalogMultiplier"
    category = "Control / Analog"
    icon = "✖️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_a", PortDirection.IN, StreamPhase.SIGNAL, "Signal A (Multiplier)", required=True),
            Port("in_b", PortDirection.IN, StreamPhase.SIGNAL, "Signal B (Multiplier)", required=False),
            Port("in_div", PortDirection.IN, StreamPhase.SIGNAL, "Signal Divisor (Denominator, optional)", required=False),
            Port("out_prod", PortDirection.OUT, StreamPhase.SIGNAL, "Product / Ratio Output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "gain": {"type": float, "default": 1.0, "label": "Multiplier Gain"},
            "bias": {"type": float, "default": 0.0, "label": "Bias / Offset"},
            "clamp_min": {"type": float, "default": -1000000.0, "label": "Clamp Output Min"},
            "clamp_max": {"type": float, "default": 1000000.0, "label": "Clamp Output Max"},
        }

    def initialize(self):
        self.state = {
            "in_a": 0.0,
            "in_b": 0.0,
            "in_div": 1.0,
            "output_prod": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        ia = inlet_streams.get("in_a")
        ib = inlet_streams.get("in_b")
        idiv = inlet_streams.get("in_div")
        out_s = outlet_streams.get("out_prod")

        va = ia.signal_value if ia else 1.0
        vb = ib.signal_value if ib else 1.0
        vdiv = idiv.signal_value if idiv else 1.0

        if abs(vdiv) < 1e-9:
            vdiv = 1e-9 if vdiv >= 0 else -1e-9

        gain = float(self.parameters.get("gain", 1.0))
        bias = float(self.parameters.get("bias", 0.0))
        c_min = float(self.parameters.get("clamp_min", -1000000.0))
        c_max = float(self.parameters.get("clamp_max", 1000000.0))

        raw_prod = gain * (va * vb / vdiv) + bias
        res = max(c_min, min(c_max, raw_prod))

        self.state["in_a"] = round(va, 2)
        self.state["in_b"] = round(vb, 2)
        self.state["in_div"] = round(vdiv, 2)
        self.state["output_prod"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
