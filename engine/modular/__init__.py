"""
Modular Process Simulation Engine Package
Supports arbitrary flowsheets with unit operation blocks, thermodynamic streams,
topological sorting, tear stream solvers, and dynamic ODE integration.
"""

from .stream import ProcessStream, StreamPhase
from .block_base import BlockBase, Port, PortDirection
from .flowsheet_graph import FlowsheetGraph
from .solver import FlowsheetSolver
from .manager import ModularEngineManager
from .library import BLOCK_REGISTRY, get_block_class, get_component_catalog
from .templates import get_template_manifest, load_template_graph

__all__ = [
    "ProcessStream",
    "StreamPhase",
    "BlockBase",
    "Port",
    "PortDirection",
    "FlowsheetGraph",
    "FlowsheetSolver",
    "ModularEngineManager",
    "BLOCK_REGISTRY",
    "get_block_class",
    "get_component_catalog",
    "get_template_manifest",
    "load_template_graph",
]
