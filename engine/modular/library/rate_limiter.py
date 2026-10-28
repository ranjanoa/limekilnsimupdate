"""
Analog Slew-Rate Limiter / Ramp Generator.
Restricts maximum rate-of-change (rising and falling slopes) of control signals.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class RateLimiter(BlockBase):
    """
    Analog Slew-Rate Limiter / Ramp Generator.
    Restricts maximum rate-of-change (rising and falling slopes) of control signals.
    """
    block_type = "RateLimiter"
    category = "Control / Analog"
    icon = "📐"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_signal", PortDirection.IN, StreamPhase.SIGNAL, "Input demand signal", required=True),
            Port("out_ramped", PortDirection.OUT, StreamPhase.SIGNAL, "Rate-limited ramped output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "max_rate_up_per_s": {"type": float, "default": 5.0, "min": 0.01, "max": 1000.0, "unit": "EU/s", "label": "Max Ramp Up Rate"},
            "max_rate_down_per_s": {"type": float, "default": 10.0, "min": 0.01, "max": 1000.0, "unit": "EU/s", "label": "Max Ramp Down Rate"},
        }

    def initialize(self):
        self.current_val = 0.0
        self.state = {
            "demand_val": 0.0,
            "ramped_val": 0.0,
            "slewing": False,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_signal")
        out_s = outlet_streams.get("out_ramped")

        target = in_s.signal_value if in_s else 0.0
        self.current_val = target
        self.state["demand_val"] = round(target, 2)
        self.state["ramped_val"] = round(target, 2)
        self.state["slewing"] = False

        if out_s:
            out_s.update_state(signal_value=target, temperature_c=target, mass_flow_tph=0.0)
        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        in_s = inlet_streams.get("in_signal")
        out_s = outlet_streams.get("out_ramped")

        target = in_s.signal_value if in_s else 0.0
        rate_up = max(0.001, float(self.parameters.get("max_rate_up_per_s", 5.0)))
        rate_down = max(0.001, float(self.parameters.get("max_rate_down_per_s", 10.0)))

        delta = target - self.current_val
        max_up = rate_up * dt
        max_down = rate_down * dt

        if delta > max_up:
            self.current_val += max_up
            slewing = True
        elif delta < -max_down:
            self.current_val -= max_down
            slewing = True
        else:
            self.current_val = target
            slewing = False

        self.state["demand_val"] = round(target, 2)
        self.state["ramped_val"] = round(self.current_val, 2)
        self.state["slewing"] = slewing

        if out_s:
            out_s.update_state(signal_value=self.current_val, temperature_c=self.current_val, mass_flow_tph=0.0)
