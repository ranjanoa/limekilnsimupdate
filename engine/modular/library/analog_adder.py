"""
Analog Multi-Input Weighted Summation Block.
Calculates weighted sum of up to 4 analog inputs:
Output = (k1 * in_1) + (k2 * in_2) + (k3 * in_3) + (k4 * in_4) + bias
with optional output clamping.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogAdder(BlockBase):
    """
    Analog Multi-Input Weighted Summation Block.
    Calculates weighted sum of up to 4 analog inputs:
    Output = (k1 * in_1) + (k2 * in_2) + (k3 * in_3) + (k4 * in_4) + bias
    with optional output clamping.
    """
    block_type = "AnalogAdder"
    category = "Control / Analog"
    icon = "➕"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_1", PortDirection.IN, StreamPhase.SIGNAL, "Primary Signal 1", required=True),
            Port("in_2", PortDirection.IN, StreamPhase.SIGNAL, "Secondary Signal 2", required=False),
            Port("in_3", PortDirection.IN, StreamPhase.SIGNAL, "Signal 3 (optional)", required=False),
            Port("in_4", PortDirection.IN, StreamPhase.SIGNAL, "Signal 4 (optional)", required=False),
            Port("out_sum", PortDirection.OUT, StreamPhase.SIGNAL, "Summation Output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "k1": {"type": float, "default": 1.0, "label": "Weight Gain k1 (for in_1)"},
            "k2": {"type": float, "default": 1.0, "label": "Weight Gain k2 (for in_2)"},
            "k3": {"type": float, "default": 1.0, "label": "Weight Gain k3 (for in_3)"},
            "k4": {"type": float, "default": 1.0, "label": "Weight Gain k4 (for in_4)"},
            "bias": {"type": float, "default": 0.0, "label": "Bias / Offset"},
            "clamp_min": {"type": float, "default": -1000000.0, "label": "Clamp Output Min"},
            "clamp_max": {"type": float, "default": 1000000.0, "label": "Clamp Output Max"},
        }

    def initialize(self):
        self.state = {
            "in_1": 0.0,
            "in_2": 0.0,
            "in_3": 0.0,
            "in_4": 0.0,
            "output_sum": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        i1 = inlet_streams.get("in_1")
        i2 = inlet_streams.get("in_2")
        i3 = inlet_streams.get("in_3")
        i4 = inlet_streams.get("in_4")
        out_s = outlet_streams.get("out_sum")

        v1 = i1.signal_value if i1 else 0.0
        v2 = i2.signal_value if i2 else 0.0
        v3 = i3.signal_value if i3 else 0.0
        v4 = i4.signal_value if i4 else 0.0

        k1 = float(self.parameters.get("k1", 1.0))
        k2 = float(self.parameters.get("k2", 1.0))
        k3 = float(self.parameters.get("k3", 1.0))
        k4 = float(self.parameters.get("k4", 1.0))
        bias = float(self.parameters.get("bias", 0.0))
        c_min = float(self.parameters.get("clamp_min", -1000000.0))
        c_max = float(self.parameters.get("clamp_max", 1000000.0))

        raw_sum = (k1 * v1) + (k2 * v2) + (k3 * v3) + (k4 * v4) + bias
        res = max(c_min, min(c_max, raw_sum))

        self.state["in_1"] = round(v1, 2)
        self.state["in_2"] = round(v2, 2)
        self.state["in_3"] = round(v3, 2)
        self.state["in_4"] = round(v4, 2)
        self.state["output_sum"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
