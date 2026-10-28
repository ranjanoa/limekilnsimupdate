"""
Modular Block Library Registry.
Central registry for all available process unit operation models.
Provides component catalog metadata for graphical flowsheet builder palette.

All 35 standard library components are modularized into individual standalone files:
- Feeding & Storage: gravimetric_feeder.py, fuel_feeder.py, silo_storage.py
- Process Equipment: cyclone.py, calciner.py, rotary_kiln.py, grate_cooler.py, fan.py, stream_sensor.py
- Flow Control: stream_mixer.py, stream_splitter.py, damper_valve.py, fuel_mixer.py, air_mixer.py, gas_mixer.py
- Analog Control & Math: pid_controller.py, lead_lag_filter.py, analog_comparator.py, signal_selector.py,
  rate_limiter.py, analog_math_block.py, process_transmitter.py, control_valve_actuator.py, analog_constant.py,
  analog_adder.py, analog_subtractor.py, analog_multiplier.py, analog_equation_block.py, analog_select.py
- Binary & Discrete Logic: logic_gate.py, rs_flip_flop.py, timer_delay.py, edge_detector.py,
  interlock_matrix.py, binary_constant.py
"""

from typing import Dict, Type, Any, List

from ..block_base import BlockBase

# Modular equipment and storage components (individual files)
from .gravimetric_feeder import GravimetricFeeder
from .fuel_feeder import FuelFeeder
from .silo_storage import SiloStorage
from .cyclone import CycloneStage
from .calciner import CalcinerReactor
from .rotary_kiln import RotaryKiln
from .grate_cooler import GrateCooler
from .fan import IDFan
from .stream_sensor import StreamSensor

# Modular flow control components (individual files)
from .stream_mixer import StreamMixer
from .stream_splitter import StreamSplitter
from .damper_valve import DamperValve
from .fuel_mixer import FuelMixer
from .air_mixer import AirMixer
from .gas_mixer import GasMixer

# Modular analog control & calculation components (individual files)
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

# Modular binary & discrete logic components (individual files)
from .logic_gate import LogicGate
from .rs_flip_flop import RSFlipFlop
from .timer_delay import TimerDelay
from .edge_detector import EdgeDetector
from .interlock_matrix import InterlockMatrix
from .binary_constant import BinaryConstant

# Custom block dynamic loader
from .custom_loader import (
    CUSTOM_BLOCK_REGISTRY,
    load_custom_components,
    validate_component_source,
    save_and_register_custom_component,
    delete_custom_component,
    get_custom_components_list,
    get_available_templates,
)

BLOCK_REGISTRY: Dict[str, Type[BlockBase]] = {
    # Process & Kiln Equipment
    "GravimetricFeeder": GravimetricFeeder,
    "FuelFeeder": FuelFeeder,
    "SiloStorage": SiloStorage,
    "CycloneStage": CycloneStage,
    "CalcinerReactor": CalcinerReactor,
    "RotaryKiln": RotaryKiln,
    "GrateCooler": GrateCooler,
    "IDFan": IDFan,
    "StreamSensor": StreamSensor,
    "StreamMixer": StreamMixer,
    "FuelMixer": FuelMixer,
    "AirMixer": AirMixer,
    "GasMixer": GasMixer,
    "StreamSplitter": StreamSplitter,
    "DamperValve": DamperValve,
    # Analog Control & Measurement Library
    "PIDController": PIDController,
    "LeadLagFilter": LeadLagFilter,
    "AnalogComparator": AnalogComparator,
    "SignalSelector": SignalSelector,
    "RateLimiter": RateLimiter,
    "AnalogMathBlock": AnalogMathBlock,
    "ProcessTransmitter": ProcessTransmitter,
    "ControlValveActuator": ControlValveActuator,
    "AnalogConstant": AnalogConstant,
    "AnalogAdder": AnalogAdder,
    "AnalogSubtractor": AnalogSubtractor,
    "AnalogMultiplier": AnalogMultiplier,
    "AnalogEquationBlock": AnalogEquationBlock,
    "AnalogSelect": AnalogSelect,
    # Binary & Discrete Logic Library
    "LogicGate": LogicGate,
    "RSFlipFlop": RSFlipFlop,
    "TimerDelay": TimerDelay,
    "EdgeDetector": EdgeDetector,
    "InterlockMatrix": InterlockMatrix,
    "BinaryConstant": BinaryConstant,
}

# Auto-discover and register custom unit operation components from custom/ folder
load_custom_components(BLOCK_REGISTRY)


def get_block_class(block_type: str) -> Type[BlockBase]:
    """Retrieves unit operation class by block type string."""
    if block_type in BLOCK_REGISTRY:
        return BLOCK_REGISTRY[block_type]
    # Check if a new custom component was placed on disk and not yet loaded
    load_custom_components(BLOCK_REGISTRY)
    if block_type in BLOCK_REGISTRY:
        return BLOCK_REGISTRY[block_type]
    raise KeyError(f"Block type '{block_type}' is not registered in block library.")


def get_component_catalog() -> List[Dict[str, Any]]:
    """
    Returns full component schema catalog for graphical flowsheet palette.
    Includes category, ports, parameters, icons, and is_custom indicator.
    """
    # Ensure any new custom components created on disk are discovered
    load_custom_components(BLOCK_REGISTRY)
    catalog = []
    for type_name, cls in BLOCK_REGISTRY.items():
        # Instantiate temporary block to inspect ports and schemas
        temp_inst = cls(block_id="catalog_temp")
        clean_params = {}
        for p_name, p_def in temp_inst.parameter_schema.items():
            param_copy = dict(p_def)
            if "type" in param_copy and isinstance(param_copy["type"], type):
                param_copy["type"] = param_copy["type"].__name__
            clean_params[p_name] = param_copy

        catalog.append({
            "type": type_name,
            "category": cls.category,
            "icon": cls.icon,
            "ports": [p.to_dict() for p in temp_inst.ports.values()],
            "parameters": clean_params,
            "is_custom": getattr(cls, "is_custom", False),
        })
    return catalog


__all__ = [
    "BLOCK_REGISTRY",
    "CUSTOM_BLOCK_REGISTRY",
    "get_block_class",
    "get_component_catalog",
    "load_custom_components",
    "validate_component_source",
    "save_and_register_custom_component",
    "delete_custom_component",
    "get_custom_components_list",
    "get_available_templates",
    "GravimetricFeeder",
    "FuelFeeder",
    "SiloStorage",
    "CycloneStage",
    "CalcinerReactor",
    "RotaryKiln",
    "GrateCooler",
    "IDFan",
    "StreamSensor",
    "StreamMixer",
    "FuelMixer",
    "AirMixer",
    "GasMixer",
    "StreamSplitter",
    "DamperValve",
    "PIDController",
    "LeadLagFilter",
    "AnalogComparator",
    "SignalSelector",
    "RateLimiter",
    "AnalogMathBlock",
    "ProcessTransmitter",
    "ControlValveActuator",
    "LogicGate",
    "RSFlipFlop",
    "TimerDelay",
    "EdgeDetector",
    "InterlockMatrix",
    "AnalogConstant",
    "AnalogAdder",
    "AnalogSubtractor",
    "AnalogMultiplier",
    "AnalogEquationBlock",
    "AnalogSelect",
    "BinaryConstant",
    "safe_eval_math_expression",
]
