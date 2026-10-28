"""
Dynamic Math Equation & Algebraic Expression Block.
Evaluates arbitrary user-defined mathematical formulas f(A, B, C, D):
Supports standard arithmetic, powers, and math functions (sqrt, exp, log, sin, cos, abs, min, max).
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase
from .math_evaluator import safe_eval_math_expression


class AnalogEquationBlock(BlockBase):
    """
    Dynamic Math Equation & Algebraic Expression Block.
    Evaluates arbitrary user-defined mathematical formulas f(A, B, C, D):
    Supports standard arithmetic, powers, and math functions (sqrt, exp, log, sin, cos, abs, min, max).
    Example formulas:
      - 'A + B'
      - 'A - B'
      - '(A + B + C) / 3'
      - 'sqrt(A^2 + B^2)'
      - '100 * (A - B) / max(0.1, C)'
      - 'A * exp(-B / (C + 273.15))'
    """
    block_type = "AnalogEquationBlock"
    category = "Control / Analog"
    icon = "📐"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_a", PortDirection.IN, StreamPhase.SIGNAL, "Variable A input", required=False),
            Port("in_b", PortDirection.IN, StreamPhase.SIGNAL, "Variable B input", required=False),
            Port("in_c", PortDirection.IN, StreamPhase.SIGNAL, "Variable C input", required=False),
            Port("in_d", PortDirection.IN, StreamPhase.SIGNAL, "Variable D input", required=False),
            Port("out_val", PortDirection.OUT, StreamPhase.SIGNAL, "Equation result output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "equation": {"type": str, "default": "A + B", "label": "Algebraic Formula f(A, B, C, D)"},
            "clamp_min": {"type": float, "default": -1000000.0, "label": "Clamp Output Min"},
            "clamp_max": {"type": float, "default": 1000000.0, "label": "Clamp Output Max"},
            "description": {"type": str, "default": "Custom Calculation", "label": "Tag Description"},
        }

    def initialize(self):
        eq = str(self.parameters.get("equation", "A + B"))
        self.state = {
            "in_a": 0.0,
            "in_b": 0.0,
            "in_c": 0.0,
            "in_d": 0.0,
            "equation": eq,
            "output_val": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        ia = inlet_streams.get("in_a")
        ib = inlet_streams.get("in_b")
        ic = inlet_streams.get("in_c")
        id_s = inlet_streams.get("in_d")
        out_s = outlet_streams.get("out_val")

        va = ia.signal_value if ia else 0.0
        vb = ib.signal_value if ib else 0.0
        vc = ic.signal_value if ic else 0.0
        vd = id_s.signal_value if id_s else 0.0

        eq = str(self.parameters.get("equation", "A + B"))
        c_min = float(self.parameters.get("clamp_min", -1000000.0))
        c_max = float(self.parameters.get("clamp_max", 1000000.0))

        vars_map = {
            "A": va, "B": vb, "C": vc, "D": vd,
            "a": va, "b": vb, "c": vc, "d": vd,
        }
        raw_res = safe_eval_math_expression(eq, vars_map)
        res = max(c_min, min(c_max, raw_res))

        self.state["in_a"] = round(va, 2)
        self.state["in_b"] = round(vb, 2)
        self.state["in_c"] = round(vc, 2)
        self.state["in_d"] = round(vd, 2)
        self.state["equation"] = eq
        self.state["output_val"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
