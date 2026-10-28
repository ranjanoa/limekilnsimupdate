"""
Modulating Control Valve & Actuator.
Bridges an incoming analog control signal (0-100% positioner)
to throttle a physical gas/air/liquid flow stream.
"""

from typing import Dict, List, Any
import copy
import math
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class ControlValveActuator(BlockBase):
    """
    Modulating Control Valve & Actuator.
    Bridges an incoming analog control signal (0-100% positioner)
    to throttle a physical gas/air/liquid flow stream.
    """
    block_type = "ControlValveActuator"
    category = "Control / Analog"
    icon = "🚰"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_fluid", PortDirection.IN, StreamPhase.ANY, "Fluid/gas stream inlet", required=True),
            Port("in_signal", PortDirection.IN, StreamPhase.SIGNAL, "Actuator control demand (0-100%)", required=False),
            Port("out_fluid", PortDirection.OUT, StreamPhase.ANY, "Throttled discharge stream", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "manual_position_pct": {"type": float, "default": 50.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Manual Position Setpoint"},
            "characteristic": {"type": str, "default": "EQUAL_PERCENTAGE", "label": "Trim Characteristic (LINEAR/EQUAL_PERCENTAGE/QUICK_OPEN)"},
            "pressure_drop_design_mbar": {"type": float, "default": 10.0, "min": 0.1, "max": 200.0, "unit": "mbar", "label": "Design Delta-P (mbar)"},
            "use_signal_input": {"type": bool, "default": True, "label": "Control from in_signal wire (True) or Manual Position (False)"},
        }

    def initialize(self):
        self.state = {
            "valve_position_pct": 50.0,
            "flow_coefficient_fraction": 0.5,
            "actual_flow_tph": 50.0,
            "dp_mbar": 5.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_fl = inlet_streams.get("in_fluid")
        in_sig = inlet_streams.get("in_signal")
        out_fl = outlet_streams.get("out_fluid")

        use_sig = bool(self.parameters.get("use_signal_input", True))
        if use_sig and in_sig:
            pos = max(0.0, min(100.0, in_sig.signal_value))
        else:
            pos = float(self.parameters.get("manual_position_pct", 50.0))

        char = str(self.parameters.get("characteristic", "EQUAL_PERCENTAGE")).upper()
        norm_pos = pos / 100.0

        if char == "LINEAR":
            flow_fraction = norm_pos
        elif char == "QUICK_OPEN":
            flow_fraction = math.sqrt(norm_pos) if norm_pos > 0 else 0.0
        else:
            # EQUAL_PERCENTAGE: R^(x-1), Rangeability R ~ 30
            R = 30.0
            flow_fraction = (R ** (norm_pos - 1.0)) if norm_pos > 0.01 else 0.0

        m_in = in_fl.mass_flow_tph if in_fl else 100.0
        t_in = in_fl.temperature_c if in_fl else 25.0
        p_in = in_fl.pressure_mbar if in_fl else 0.0

        m_out = m_in * max(0.001, flow_fraction)
        dp_des = float(self.parameters.get("pressure_drop_design_mbar", 10.0))
        dp = dp_des * (1.0 / max(0.05, flow_fraction) ** 2) * 0.1

        self.state["valve_position_pct"] = round(pos, 1)
        self.state["flow_coefficient_fraction"] = round(flow_fraction, 3)
        self.state["actual_flow_tph"] = round(m_out, 2)
        self.state["dp_mbar"] = round(dp, 2)

        if out_fl and in_fl:
            out_fl.update_state(
                mass_flow_tph=m_out,
                temperature_c=t_in,
                pressure_mbar=p_in - dp,
                composition=copy.deepcopy(in_fl.composition),
            )

        return outlet_streams
