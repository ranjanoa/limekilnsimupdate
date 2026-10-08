"""
Modular Block Library Registry.
Central registry for all available process unit operation models.
Provides component catalog metadata for graphical flowsheet builder palette.
"""

from typing import Dict, Type, Any, List

from ..block_base import BlockBase
from .feeder import GravimetricFeeder, FuelFeeder, SiloStorage
from .cyclone import CycloneStage
from .calciner import CalcinerReactor
from .rotary_kiln import RotaryKiln
from .grate_cooler import GrateCooler
from .fan import IDFan
from .mixer_splitter import StreamMixer, StreamSplitter, DamperValve, FuelMixer, AirMixer, GasMixer

BLOCK_REGISTRY: Dict[str, Type[BlockBase]] = {
    "GravimetricFeeder": GravimetricFeeder,
    "FuelFeeder": FuelFeeder,
    "SiloStorage": SiloStorage,
    "CycloneStage": CycloneStage,
    "CalcinerReactor": CalcinerReactor,
    "RotaryKiln": RotaryKiln,
    "GrateCooler": GrateCooler,
    "IDFan": IDFan,
    "StreamMixer": StreamMixer,
    "FuelMixer": FuelMixer,
    "AirMixer": AirMixer,
    "GasMixer": GasMixer,
    "StreamSplitter": StreamSplitter,
    "DamperValve": DamperValve,
}


def get_block_class(block_type: str) -> Type[BlockBase]:
    """Retrieves unit operation class by block type string."""
    if block_type in BLOCK_REGISTRY:
        return BLOCK_REGISTRY[block_type]
    raise KeyError(f"Block type '{block_type}' is not registered in block library.")


def get_component_catalog() -> List[Dict[str, Any]]:
    """
    Returns full component schema catalog for graphical flowsheet palette.
    Includes category, ports, parameters, and icons.
    """
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
        })
    return catalog


__all__ = [
    "BLOCK_REGISTRY",
    "get_block_class",
    "get_component_catalog",
    "GravimetricFeeder",
    "FuelFeeder",
    "SiloStorage",
    "CycloneStage",
    "CalcinerReactor",
    "RotaryKiln",
    "GrateCooler",
    "IDFan",
    "StreamMixer",
    "FuelMixer",
    "AirMixer",
    "GasMixer",
    "StreamSplitter",
    "DamperValve",
]
