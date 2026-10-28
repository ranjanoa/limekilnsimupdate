"""
Process Damper / Control Valve.
Modulates gas draft and flow restriction.
"""

from typing import Dict, List, Any
import copy
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class DamperValve(BlockBase):
    """
    Process Damper / Control Valve.
    Modulates gas draft and flow restriction.
    """
    block_type = "DamperValve"
    category = "Flow Control"
    icon = "sliders"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_stream", PortDirection.IN, StreamPhase.GAS, "Upstream duct/pipe", required=True),
            Port("out_stream", PortDirection.OUT, StreamPhase.GAS, "Downstream throttled duct", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "opening_pct": {"type": float, "default": 80.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Damper Opening"},
            "dp_nominal_mbar": {"type": float, "default": 2.0, "min": 0.1, "max": 20.0, "unit": "mbar", "label": "Nominal Pressure Drop"},
        }

    def initialize(self):
        self.state = {
            "actual_dp_mbar": 2.0,
            "opening_pct": 80.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_stream")
        out_stream = outlet_streams.get("out_stream")

        if not in_stream:
            return outlet_streams

        opening = max(1.0, float(self.parameters.get("opening_pct", 80.0))) / 100.0
        dp_nom = float(self.parameters.get("dp_nominal_mbar", 2.0))
        actual_dp = dp_nom / (opening ** 2)

        self.state["actual_dp_mbar"] = round(actual_dp, 2)
        self.state["opening_pct"] = round(opening * 100.0, 1)

        if out_stream:
            out_stream.phase = in_stream.phase
            out_stream.update_state(
                mass_flow_tph=in_stream.mass_flow_tph,
                temperature_c=in_stream.temperature_c,
                pressure_mbar=in_stream.pressure_mbar - actual_dp,
                composition=copy.deepcopy(in_stream.composition),
            )

        return outlet_streams
