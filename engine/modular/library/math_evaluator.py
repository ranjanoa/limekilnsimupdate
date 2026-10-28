"""
Safe Algebraic Equation Evaluator (AST Sandbox).
Parses and evaluates mathematical formulas f(A, B, C, D) without unsafe eval().
"""

from typing import Dict
import math
import ast
import operator

_MATH_FUNCS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "ceil": math.ceil,
    "floor": math.floor,
    "pow": math.pow,
}

_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval_math_expression(expr: str, var_dict: Dict[str, float]) -> float:
    """
    Safely parses and evaluates algebraic expressions without using unsafe eval().
    Supports: A, B, C, D, constants, pi, e, +, -, *, /, %, ^, **, and math functions.
    """
    if not expr or not str(expr).strip():
        return 0.0

    # Replace ^ with ** for intuitive power syntax
    cleaned = str(expr).strip().replace("^", "**")

    try:
        parsed = ast.parse(cleaned, mode="eval")
    except Exception:
        return 0.0

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            return 0.0
        elif isinstance(node, ast.Name):
            name_lower = node.id.lower()
            name_upper = node.id.upper()
            if node.id in var_dict:
                return float(var_dict[node.id])
            elif name_upper in var_dict:
                return float(var_dict[name_upper])
            elif name_lower in var_dict:
                return float(var_dict[name_lower])
            elif name_lower == "pi":
                return math.pi
            elif name_lower == "e":
                return math.e
            return 0.0
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in _SAFE_OPERATORS:
                val = _eval(node.operand)
                return _SAFE_OPERATORS[op_type](val)
            raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in _SAFE_OPERATORS:
                left = _eval(node.left)
                right = _eval(node.right)
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod):
                    if abs(right) < 1e-12:
                        return 0.0
                if op_type == ast.Pow:
                    if abs(left) > 1e10 or abs(right) > 100:
                        return 0.0
                return _SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id.lower() in _MATH_FUNCS:
                fn = _MATH_FUNCS[node.func.id.lower()]
                args = [_eval(arg) for arg in node.args]
                try:
                    return float(fn(*args))
                except Exception:
                    return 0.0
            raise ValueError(f"Function {node.func} is not allowed")
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")

    try:
        res = float(_eval(parsed))
        if math.isnan(res) or math.isinf(res):
            return 0.0
        return res
    except Exception:
        return 0.0
