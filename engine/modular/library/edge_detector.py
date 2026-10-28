"""
Edge Trigger / One-Shot Transition Pulse Detector.
Detects Rising Edge (0->1), Falling Edge (1->0), or Both transitions.
Outputs a single simulation cycle pulse True.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class EdgeDetector(BlockBase):
    """
    Edge Trigger / One-Shot Transition Pulse Detector.
    Detects Rising Edge (0->1), Falling Edge (1->0), or Both transitions.
    Outputs a single simulation cycle pulse True.
    """
    block_type = "EdgeDetector"
    category = "Control / Binary"
    icon = "⚡"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_signal", PortDirection.IN, StreamPhase.BINARY, "Binary Clock / Signal Input", required=True),
            Port("out_pulse", PortDirection.OUT, StreamPhase.BINARY, "Single-cycle pulse output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "edge_mode": {"type": str, "default": "RISING", "label": "Edge Detection Mode (RISING/FALLING/BOTH)"},
        }

    def initialize(self):
        self.prev_signal = False
        self.pulse = False
        self.state = {
            "current_signal": False,
            "pulse_out": False,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_signal")
        out_p = outlet_streams.get("out_pulse")

        sig = in_s.binary_state if in_s else False
        self.prev_signal = sig
        self.pulse = False

        self.state["current_signal"] = sig
        self.state["pulse_out"] = False

        if out_p:
            out_p.update_state(binary_state=False, signal_value=0.0)
        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        in_s = inlet_streams.get("in_signal")
        out_p = outlet_streams.get("out_pulse")

        sig = in_s.binary_state if in_s else False
        mode = str(self.parameters.get("edge_mode", "RISING")).upper()

        if mode == "FALLING":
            pulse = self.prev_signal and not sig
        elif mode == "BOTH":
            pulse = (sig != self.prev_signal)
        else:
            # RISING
            pulse = sig and not self.prev_signal

        self.prev_signal = sig
        self.pulse = pulse
        self.state["current_signal"] = sig
        self.state["pulse_out"] = pulse

        if out_p:
            out_p.update_state(binary_state=pulse, signal_value=1.0 if pulse else 0.0)
