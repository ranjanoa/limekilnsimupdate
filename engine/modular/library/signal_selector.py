"""
Auctioneering Signal Selector.
Selects MIN, MAX, or AVERAGE among up to three incoming analog signals.
Commonly used for redundant temperature pyrometer sensors and draft auctioneering.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class SignalSelector(BlockBase):
    """
    Auctioneering Signal Selector.
    Selects MIN, MAX, or AVERAGE among up to three incoming analog signals.
    Commonly used for redundant temperature pyrometer sensors and draft auctioneering.
    """
    block_type = "SignalSelector"
    category = "Control / Analog"
    icon = "🔀"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_a", PortDirection.IN, StreamPhase.SIGNAL, "Signal Channel A", required=True),
            Port("in_b", PortDirection.IN, StreamPhase.SIGNAL, "Signal Channel B", required=True),
            Port("in_c", PortDirection.IN, StreamPhase.SIGNAL, "Signal Channel C (optional)", required=False),
            Port("out_selected", PortDirection.OUT, StreamPhase.SIGNAL, "Selected auctioneered output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "mode": {"type": str, "default": "MAX", "label": "Selection Mode (MIN/MAX/AVERAGE)"},
        }

    def initialize(self):
        self.state = {
            "channel_a": 0.0,
            "channel_b": 0.0,
            "channel_c": 0.0,
            "selected_value": 0.0,
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
        out_s = outlet_streams.get("out_selected")

        val_a = in_a.signal_value if in_a else 0.0
        val_b = in_b.signal_value if in_b else 0.0
        values = [val_a, val_b]
        if in_c:
            values.append(in_c.signal_value)

        mode = str(self.parameters.get("mode", "MAX")).upper()
        if mode == "MIN":
            res = min(values)
        elif mode == "AVERAGE":
            res = sum(values) / len(values)
        else:
            res = max(values)

        self.state["channel_a"] = round(val_a, 2)
        self.state["channel_b"] = round(val_b, 2)
        self.state["channel_c"] = round(in_c.signal_value, 2) if in_c else 0.0
        self.state["selected_value"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
