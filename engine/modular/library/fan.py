"""
IDFan: Induced draft process fan modeling centrifugal fan curve, damper throttling,
draft pressure generation, and electrical motor power consumption.
"""

from typing import Dict, List, Any
import copy

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class IDFan(BlockBase):
    """
    Induced Draft (ID) Process Fan.
    Drives negative draft throughout the preheater string and rotary kiln system.
    """
    block_type = "IDFan"
    category = "Draft / Fans"
    icon = "fan"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_gas", PortDirection.IN, StreamPhase.GAS, "Flue gas suction from preheater top stage", required=True),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Exhaust gas discharge to baghouse / main stack", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "design_flow_nm3h": {"type": float, "default": 350000.0, "min": 50000.0, "max": 800000.0, "unit": "Nm³/h", "label": "Design Flow Capacity"},
            "design_dp_mbar": {"type": float, "default": 65.0, "min": 10.0, "max": 120.0, "unit": "mbar", "label": "Design Differential Pressure"},
            "damper_pct": {"type": float, "default": 82.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Inlet Damper Position"},
            "motor_rated_kw": {"type": float, "default": 2500.0, "min": 200.0, "max": 6000.0, "unit": "kW", "label": "Motor Nominal Power"},
            "fan_efficiency": {"type": float, "default": 0.78, "min": 0.40, "max": 0.90, "unit": "-", "label": "Aerodynamic Efficiency"},
        }

    def initialize(self):
        self.state = {
            "actual_flow_nm3h": 268500.0,
            "fan_dp_mbar": 58.5,
            "motor_power_kw": 1845.0,
            "motor_current_a": 195.0,
            "inlet_draft_mbar": -56.0,
            "outlet_draft_mbar": 2.5,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_gas = inlet_streams.get("in_gas")
        out_gas = outlet_streams.get("out_gas")

        m_gas = in_gas.mass_flow_tph if in_gas else 378.0
        t_gas = in_gas.temperature_c if in_gas else 330.0
        p_in = in_gas.pressure_mbar if in_gas else -56.0

        damper = float(self.parameters.get("damper_pct", 82.0)) / 100.0
        dp_des = float(self.parameters.get("design_dp_mbar", 65.0))
        eff = float(self.parameters.get("fan_efficiency", 0.78))
        v_nm3h = in_gas.volume_flow_nm3h if in_gas and in_gas.volume_flow_nm3h else (m_gas * 1000.0 / 1.34)

        # Dynamic differential head based on damper throttling
        dp_actual = dp_des * (damper ** 1.8)
        p_out = p_in + dp_actual

        # Aerodynamic shaft power: P = V_m3_s * dp_Pa / eff
        # dp_Pa = dp_mbar * 100.0
        # V_actual_m3_s = (V_nm3h / 3600.0) * ((T + 273.15) / 273.15)
        v_act_m3_s = (v_nm3h / 3600.0) * ((t_gas + 273.15) / 273.15)
        dp_pa = dp_actual * 100.0
        power_kw = (v_act_m3_s * dp_pa) / (eff * 1000.0)
        power_kw = min(float(self.parameters.get("motor_rated_kw", 2500.0)), max(100.0, power_kw))

        # Update block state
        self.state["actual_flow_nm3h"] = round(v_nm3h, 1)
        self.state["fan_dp_mbar"] = round(dp_actual, 2)
        self.state["motor_power_kw"] = round(power_kw, 1)
        self.state["motor_current_a"] = round(power_kw / (0.690 * 1.732 * 0.88), 1)
        self.state["inlet_draft_mbar"] = round(p_in, 1)
        self.state["outlet_draft_mbar"] = round(p_out, 1)

        # Update outlet stream
        if out_gas:
            comp_gas = copy.deepcopy(in_gas.composition) if in_gas else {}
            out_gas.update_state(
                mass_flow_tph=m_gas,
                temperature_c=t_gas + 2.0,  # Slight fan friction work heat
                pressure_mbar=p_out,
                composition=comp_gas,
            )

        return outlet_streams
