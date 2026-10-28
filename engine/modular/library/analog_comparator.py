"""
Analog Threshold Comparator & Alarm Trip Block.
Compares process variable against High and Low limits with hysteresis.
Generates binary trip/alarm signals (HI, LO, NORMAL).
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogComparator(BlockBase):
    """
    Analog Threshold Comparator & Alarm Trip Block.
    Compares process variable against High and Low limits with hysteresis.
    Generates binary trip/alarm signals (HI, LO, NORMAL).
    """
    block_type = "AnalogComparator"
    category = "Control / Analog"
    icon = "⚠️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_val", PortDirection.IN, StreamPhase.SIGNAL, "Analog input signal", required=True),
            Port("out_hi", PortDirection.OUT, StreamPhase.BINARY, "High alarm trip state (1=Trip)", required=True),
            Port("out_lo", PortDirection.OUT, StreamPhase.BINARY, "Low alarm trip state (1=Trip)", required=False),
            Port("out_normal", PortDirection.OUT, StreamPhase.BINARY, "Normal in-bounds state (1=OK)", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "hi_limit": {"type": float, "default": 80.0, "min": -10000.0, "max": 10000.0, "label": "High Alarm Threshold"},
            "lo_limit": {"type": float, "default": 20.0, "min": -10000.0, "max": 10000.0, "label": "Low Alarm Threshold"},
            "hysteresis": {"type": float, "default": 2.0, "min": 0.0, "max": 100.0, "label": "Deadband Hysteresis"},
        }

    def initialize(self):
        self.state = {
            "input_val": 50.0,
            "alarm_hi": False,
            "alarm_lo": False,
            "status": "NORMAL",
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_val")
        out_hi = outlet_streams.get("out_hi")
        out_lo = outlet_streams.get("out_lo")
        out_norm = outlet_streams.get("out_normal")

        val = in_s.signal_value if in_s else (in_s.temperature_c if in_s else 50.0)
        hi = float(self.parameters.get("hi_limit", 80.0))
        lo = float(self.parameters.get("lo_limit", 20.0))
        hys = float(self.parameters.get("hysteresis", 2.0))

        # Hysteresis comparison logic
        prev_hi = bool(self.state.get("alarm_hi", False))
        prev_lo = bool(self.state.get("alarm_lo", False))

        is_hi = val > hi if not prev_hi else val > (hi - hys)
        is_lo = val < lo if not prev_lo else val < (lo + hys)
        is_normal = not is_hi and not is_lo

        self.state["input_val"] = round(val, 2)
        self.state["alarm_hi"] = is_hi
        self.state["alarm_lo"] = is_lo
        self.state["status"] = "HIGH_ALARM" if is_hi else ("LOW_ALARM" if is_lo else "NORMAL")

        if out_hi:
            out_hi.update_state(binary_state=is_hi, signal_value=1.0 if is_hi else 0.0)
        if out_lo:
            out_lo.update_state(binary_state=is_lo, signal_value=1.0 if is_lo else 0.0)
        if out_norm:
            out_norm.update_state(binary_state=is_normal, signal_value=1.0 if is_normal else 0.0)

        return outlet_streams
