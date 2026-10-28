"""
Analog Control & Logic Library for Modular Flowsheet Simulation.
Aggregates and re-exports all modular analog components for backward compatibility:
- PIDController (from .pid_controller)
- LeadLagFilter (from .lead_lag_filter)
- AnalogComparator (from .analog_comparator)
- SignalSelector (from .signal_selector)
- RateLimiter (from .rate_limiter)
- AnalogMathBlock (from .analog_math_block)
- ProcessTransmitter (from .process_transmitter)
- ControlValveActuator (from .control_valve_actuator)
- AnalogConstant (from .analog_constant)
- AnalogAdder (from .analog_adder)
- AnalogSubtractor (from .analog_subtractor)
- AnalogMultiplier (from .analog_multiplier)
- AnalogEquationBlock (from .analog_equation_block)
- AnalogSelect (from .analog_select)
- safe_eval_math_expression (from .math_evaluator)
"""

from .pid_controller import PIDController
from .lead_lag_filter import LeadLagFilter
from .analog_comparator import AnalogComparator
from .signal_selector import SignalSelector
from .rate_limiter import RateLimiter
from .analog_math_block import AnalogMathBlock
from .process_transmitter import ProcessTransmitter
from .control_valve_actuator import ControlValveActuator
from .analog_constant import AnalogConstant
from .analog_adder import AnalogAdder
from .analog_subtractor import AnalogSubtractor
from .analog_multiplier import AnalogMultiplier
from .analog_equation_block import AnalogEquationBlock
from .analog_select import AnalogSelect
from .math_evaluator import safe_eval_math_expression

__all__ = [
    "PIDController",
    "LeadLagFilter",
    "AnalogComparator",
    "SignalSelector",
    "RateLimiter",
    "AnalogMathBlock",
    "ProcessTransmitter",
    "ControlValveActuator",
    "AnalogConstant",
    "AnalogAdder",
    "AnalogSubtractor",
    "AnalogMultiplier",
    "AnalogEquationBlock",
    "AnalogSelect",
    "safe_eval_math_expression",
]
