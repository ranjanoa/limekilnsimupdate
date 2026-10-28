"""
First-Order Dynamic Lag / Lead-Lag Filter.
Simulates physical sensor response time, transmitter damping, and noisy PV smoothing.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class LeadLagFilter(BlockBase):
    """
    First-Order Dynamic Lag / Lead-Lag Filter.
    Simulates physical sensor response time, transmitter damping, and noisy PV smoothing.
    """
    block_type = "LeadLagFilter"
    category = "Control / Analog"
    icon = "📈"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_signal", PortDirection.IN, StreamPhase.SIGNAL, "Raw input signal", required=True),
            Port("out_signal", PortDirection.OUT, StreamPhase.SIGNAL, "Filtered output signal", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "time_constant_s": {"type": float, "default": 5.0, "min": 0.01, "max": 600.0, "unit": "s", "label": "Lag Time Constant (T1)"},
            "gain": {"type": float, "default": 1.0, "min": -100.0, "max": 100.0, "label": "Static Gain (K)"},
        }

    def initialize(self):
        self.filtered_val = 0.0
        self.state = {
            "input_val": 0.0,
            "output_val": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_signal")
        out_s = outlet_streams.get("out_signal")

        val = in_s.signal_value if in_s else (in_s.temperature_c if in_s else 0.0)
        gain = float(self.parameters.get("gain", 1.0))
        steady_out = val * gain

        self.filtered_val = steady_out
        self.state["input_val"] = round(val, 2)
        self.state["output_val"] = round(steady_out, 2)

        if out_s:
            out_s.update_state(signal_value=steady_out, temperature_c=steady_out, mass_flow_tph=0.0)
        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        in_s = inlet_streams.get("in_signal")
        out_s = outlet_streams.get("out_signal")

        val = in_s.signal_value if in_s else (in_s.temperature_c if in_s else 0.0)
        gain = float(self.parameters.get("gain", 1.0))
        t1 = max(0.01, float(self.parameters.get("time_constant_s", 5.0)))

        alpha = dt / (t1 + dt)
        self.filtered_val += alpha * ((val * gain) - self.filtered_val)

        self.state["input_val"] = round(val, 2)
        self.state["output_val"] = round(self.filtered_val, 2)

        if out_s:
            out_s.update_state(signal_value=self.filtered_val, temperature_c=self.filtered_val, mass_flow_tph=0.0)
