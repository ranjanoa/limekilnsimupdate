"""
Analog Difference / Subtractor Block.
Computes difference between positive and negative inputs:
Output = (gain_pos * in_pos) - (gain_neg * in_neg) + bias
with optional output clamping.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogSubtractor(BlockBase):
    """
    Analog Difference / Subtractor Block.
    Computes difference between positive and negative inputs:
    Output = (gain_pos * in_pos) - (gain_neg * in_neg) + bias
    with optional output clamping.
    """
    block_type = "AnalogSubtractor"
    category = "Control / Analog"
    icon = "➖"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_pos", PortDirection.IN, StreamPhase.SIGNAL, "Positive Input Signal (+)", required=True),
            Port("in_neg", PortDirection.IN, StreamPhase.SIGNAL, "Negative Input Signal (-)", required=True),
            Port("out_diff", PortDirection.OUT, StreamPhase.SIGNAL, "Difference Output (+ - -)", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "gain_pos": {"type": float, "default": 1.0, "label": "Positive Gain (k+)"},
            "gain_neg": {"type": float, "default": 1.0, "label": "Negative Gain (k-)"},
            "bias": {"type": float, "default": 0.0, "label": "Bias / Offset"},
            "clamp_min": {"type": float, "default": -1000000.0, "label": "Clamp Output Min"},
            "clamp_max": {"type": float, "default": 1000000.0, "label": "Clamp Output Max"},
        }

    def initialize(self):
        self.state = {
            "in_pos": 0.0,
            "in_neg": 0.0,
            "output_diff": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        i_pos = inlet_streams.get("in_pos")
        i_neg = inlet_streams.get("in_neg")
        out_s = outlet_streams.get("out_diff")

        vp = i_pos.signal_value if i_pos else 0.0
        vn = i_neg.signal_value if i_neg else 0.0

        gp = float(self.parameters.get("gain_pos", 1.0))
        gn = float(self.parameters.get("gain_neg", 1.0))
        bias = float(self.parameters.get("bias", 0.0))
        c_min = float(self.parameters.get("clamp_min", -1000000.0))
        c_max = float(self.parameters.get("clamp_max", 1000000.0))

        raw_diff = (gp * vp) - (gn * vn) + bias
        res = max(c_min, min(c_max, raw_diff))

        self.state["in_pos"] = round(vp, 2)
        self.state["in_neg"] = round(vn, 2)
        self.state["output_diff"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
