"""
Analog Constant / Setpoint Source Block.
Provides a continuous user-configurable constant signal value.
Used for external setpoints, fixed bias, boundary test values, or initial conditions.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogConstant(BlockBase):
    """
    Analog Constant / Setpoint Source Block.
    Provides a continuous user-configurable constant signal value.
    Used for external setpoints, fixed bias, boundary test values, or initial conditions.
    """
    block_type = "AnalogConstant"
    category = "Control / Analog"
    icon = "🔢"

    def _define_ports(self) -> List[Port]:
        return [
            Port("out_signal", PortDirection.OUT, StreamPhase.SIGNAL, "Constant analog signal output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "constant_value": {"type": float, "default": 100.0, "min": -1000000.0, "max": 1000000.0, "label": "Constant Value"},
            "engineering_unit": {"type": str, "default": "EU", "label": "Engineering Unit (°C, t/h, %, mbar)"},
            "description": {"type": str, "default": "Constant Signal", "label": "Tag Description"},
        }

    def initialize(self):
        val = float(self.parameters.get("constant_value", 100.0))
        unit = str(self.parameters.get("engineering_unit", "EU"))
        self.state = {
            "constant_value": val,
            "engineering_unit": unit,
            "output_signal": val,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        val = float(self.parameters.get("constant_value", 100.0))
        unit = str(self.parameters.get("engineering_unit", "EU"))
        out_s = outlet_streams.get("out_signal")

        self.state["constant_value"] = round(val, 3)
        self.state["engineering_unit"] = unit
        self.state["output_signal"] = round(val, 3)

        if out_s:
            out_s.update_state(signal_value=val, temperature_c=val, mass_flow_tph=0.0)
        return outlet_streams
