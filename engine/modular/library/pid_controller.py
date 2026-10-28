"""
Industrial PID Feedback Controller.
Computes manipulated variable (MV 0-100%) to regulate process variable (PV)
to setpoint (SP) using discrete parallel PID algorithm with anti-windup.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class PIDController(BlockBase):
    """
    Industrial PID Feedback Controller.
    Computes manipulated variable (MV 0-100%) to regulate process variable (PV)
    to setpoint (SP) using discrete parallel PID algorithm with anti-windup.
    """
    block_type = "PIDController"
    category = "Control / Analog"
    icon = "🕹️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("pv", PortDirection.IN, StreamPhase.SIGNAL, "Process Variable measurement (PV)", required=True),
            Port("sp_ext", PortDirection.IN, StreamPhase.SIGNAL, "External Setpoint input (optional)", required=False),
            Port("mv", PortDirection.OUT, StreamPhase.SIGNAL, "Manipulated Variable output (0-100%)", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "setpoint": {"type": float, "default": 100.0, "min": -10000.0, "max": 10000.0, "label": "Internal Setpoint (SP)"},
            "kp": {"type": float, "default": 1.2, "min": 0.01, "max": 100.0, "label": "Proportional Gain (Kp)"},
            "ti_s": {"type": float, "default": 25.0, "min": 0.1, "max": 3600.0, "unit": "s", "label": "Integral Time (Ti)"},
            "td_s": {"type": float, "default": 0.0, "min": 0.0, "max": 300.0, "unit": "s", "label": "Derivative Time (Td)"},
            "out_min": {"type": float, "default": 0.0, "min": -1000.0, "max": 1000.0, "label": "Minimum Output (%)"},
            "out_max": {"type": float, "default": 100.0, "min": -1000.0, "max": 1000.0, "label": "Maximum Output (%)"},
            "action": {"type": str, "default": "REVERSE", "label": "Control Action (DIRECT/REVERSE)"},
            "auto_mode": {"type": bool, "default": True, "label": "Auto Mode (True=Auto, False=Manual)"},
            "manual_out": {"type": float, "default": 50.0, "min": 0.0, "max": 100.0, "label": "Manual Output (%)"},
        }

    def initialize(self):
        self.integral_acc = 0.0
        self.prev_error = 0.0
        self.prev_pv = 100.0
        self.state = {
            "pv_value": 100.0,
            "sp_value": 100.0,
            "error": 0.0,
            "output_mv": 50.0,
            "p_term": 0.0,
            "i_term": 0.0,
            "d_term": 0.0,
            "mode": "AUTO",
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        pv_s = inlet_streams.get("pv")
        sp_s = inlet_streams.get("sp_ext")
        mv_s = outlet_streams.get("mv")

        pv = pv_s.signal_value if pv_s else (pv_s.temperature_c if pv_s else self.state.get("pv_value", 100.0))
        sp = sp_s.signal_value if sp_s else float(self.parameters.get("setpoint", 100.0))
        is_auto = bool(self.parameters.get("auto_mode", True))

        if not is_auto:
            mv = float(self.parameters.get("manual_out", 50.0))
            self.state["mode"] = "MANUAL"
        else:
            kp = float(self.parameters.get("kp", 1.2))
            action = str(self.parameters.get("action", "REVERSE")).upper()
            err = (sp - pv) if action == "REVERSE" else (pv - sp)
            out_min = float(self.parameters.get("out_min", 0.0))
            out_max = float(self.parameters.get("out_max", 100.0))

            # Steady state baseline: P-term + midpoint bias
            mv = 50.0 + (kp * err)
            mv = max(out_min, min(out_max, mv))
            self.state["mode"] = "AUTO"
            self.state["error"] = round(err, 2)
            self.state["p_term"] = round(kp * err, 2)

        self.state["pv_value"] = round(pv, 2)
        self.state["sp_value"] = round(sp, 2)
        self.state["output_mv"] = round(mv, 2)

        if mv_s:
            mv_s.update_state(
                signal_value=mv,
                temperature_c=mv,
                mass_flow_tph=0.0,
            )
        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        pv_s = inlet_streams.get("pv")
        sp_s = inlet_streams.get("sp_ext")
        mv_s = outlet_streams.get("mv")

        pv = pv_s.signal_value if pv_s else (pv_s.temperature_c if pv_s else self.state.get("pv_value", 100.0))
        sp = sp_s.signal_value if sp_s else float(self.parameters.get("setpoint", 100.0))
        is_auto = bool(self.parameters.get("auto_mode", True))

        out_min = float(self.parameters.get("out_min", 0.0))
        out_max = float(self.parameters.get("out_max", 100.0))

        if not is_auto:
            mv = float(self.parameters.get("manual_out", 50.0))
            self.integral_acc = mv  # Bumpless transfer tracking
            self.state["mode"] = "MANUAL"
        else:
            kp = float(self.parameters.get("kp", 1.2))
            ti = max(0.1, float(self.parameters.get("ti_s", 25.0)))
            td = max(0.0, float(self.parameters.get("td_s", 0.0)))
            action = str(self.parameters.get("action", "REVERSE")).upper()

            err = (sp - pv) if action == "REVERSE" else (pv - sp)
            p_term = kp * err

            # Integral accumulation with anti-windup clamping
            if ti > 0:
                self.integral_acc += (kp * dt / ti) * err
                self.integral_acc = max(out_min, min(out_max, self.integral_acc))
            i_term = self.integral_acc

            # Derivative on error
            d_term = 0.0
            if td > 0 and dt > 0:
                d_term = kp * td * (err - self.prev_error) / dt
            self.prev_error = err

            raw_mv = p_term + i_term + d_term
            mv = max(out_min, min(out_max, raw_mv))

            self.state["mode"] = "AUTO"
            self.state["error"] = round(err, 2)
            self.state["p_term"] = round(p_term, 2)
            self.state["i_term"] = round(i_term, 2)
            self.state["d_term"] = round(d_term, 2)

        self.state["pv_value"] = round(pv, 2)
        self.state["sp_value"] = round(sp, 2)
        self.state["output_mv"] = round(mv, 2)

        if mv_s:
            mv_s.update_state(
                signal_value=mv,
                temperature_c=mv,
                mass_flow_tph=0.0,
            )
