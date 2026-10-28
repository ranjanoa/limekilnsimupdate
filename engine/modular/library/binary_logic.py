"""
Binary & Discrete Logic Library for Modular Flowsheet Simulation.
Aggregates and re-exports all modular binary components for backward compatibility:
- LogicGate (from .logic_gate)
- RSFlipFlop (from .rs_flip_flop)
- TimerDelay (from .timer_delay)
- EdgeDetector (from .edge_detector)
- InterlockMatrix (from .interlock_matrix)
- BinaryConstant (from .binary_constant)
"""

from .logic_gate import LogicGate
from .rs_flip_flop import RSFlipFlop
from .timer_delay import TimerDelay
from .edge_detector import EdgeDetector
from .interlock_matrix import InterlockMatrix
from .binary_constant import BinaryConstant

__all__ = [
    "LogicGate",
    "RSFlipFlop",
    "TimerDelay",
    "EdgeDetector",
    "InterlockMatrix",
    "BinaryConstant",
]
