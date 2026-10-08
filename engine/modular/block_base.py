"""
BlockBase: Abstract base class for unit operation blocks in the modular flowsheet.
Defines ports, parameters, dynamic state variables, mass/energy balance evaluation,
and OPC UA tag auto-generation.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
import copy

from .stream import ProcessStream, StreamPhase


class PortDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class Port:
    """Represents a connection port on a unit operation block."""

    def __init__(
        self,
        name: str,
        direction: PortDirection,
        phase: StreamPhase,
        description: str = "",
        required: bool = True,
        connected_stream_id: Optional[int] = None,
    ):
        self.name = name
        self.direction = PortDirection(direction) if isinstance(direction, str) else direction
        self.phase = StreamPhase(phase) if isinstance(phase, str) else phase
        self.description = description
        self.required = required
        self.connected_stream_id = connected_stream_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction.value,
            "phase": self.phase.value,
            "description": self.description,
            "required": self.required,
            "connected_stream_id": self.connected_stream_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Port":
        return cls(
            name=data.get("name", ""),
            direction=data.get("direction", PortDirection.IN.value),
            phase=data.get("phase", StreamPhase.SOLID.value),
            description=data.get("description", ""),
            required=data.get("required", True),
            connected_stream_id=data.get("connected_stream_id"),
        )


class BlockBase(ABC):
    """
    Abstract Base Class for all Flowsheet Unit Operation Blocks.
    """

    block_type: str = "BlockBase"
    category: str = "General"
    icon: str = "box"

    def __init__(
        self,
        block_id: str,
        name: str = "",
        position: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.block_id = block_id
        self.name = name or f"{self.block_type}_{block_id}"
        self.position = position or {"x": 100.0, "y": 100.0}

        # Initialize Ports
        self.ports: Dict[str, Port] = {}
        for p in self._define_ports():
            self.ports[p.name] = p

        # Parameter schema and default values
        self.parameter_schema: Dict[str, Dict[str, Any]] = self._define_parameters()
        self.parameters: Dict[str, Any] = {}
        for p_name, p_def in self.parameter_schema.items():
            self.parameters[p_name] = copy.deepcopy(p_def.get("default"))

        if parameters:
            self.parameters.update(parameters)

        # Internal state dictionary
        self.state: Dict[str, Any] = {}
        self.initialize()

    @abstractmethod
    def _define_ports(self) -> List[Port]:
        """Subclasses declare their input and output ports."""
        pass

    @abstractmethod
    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Subclasses declare configurable parameter schemas with types, ranges, and defaults."""
        pass

    def initialize(self):
        """Initializes internal states, balances, and default dynamic parameters."""
        pass

    def get_inlet_ports(self) -> List[Port]:
        return [p for p in self.ports.values() if p.direction == PortDirection.IN]

    def get_outlet_ports(self) -> List[Port]:
        return [p for p in self.ports.values() if p.direction == PortDirection.OUT]

    def set_parameter(self, param_name: str, value: Any):
        """Sets a parameter with basic validation against schema."""
        if param_name in self.parameter_schema:
            schema = self.parameter_schema[param_name]
            p_type = schema.get("type", float)
            try:
                if p_type == float:
                    val = float(value)
                    if "min" in schema and val < schema["min"]:
                        val = schema["min"]
                    if "max" in schema and val > schema["max"]:
                        val = schema["max"]
                    self.parameters[param_name] = val
                elif p_type == int:
                    self.parameters[param_name] = int(value)
                elif p_type == bool:
                    self.parameters[param_name] = bool(value)
                else:
                    self.parameters[param_name] = value
            except Exception:
                self.parameters[param_name] = value
        else:
            self.parameters[param_name] = value

    @abstractmethod
    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        """
        Solves algebraic steady-state equations.
        Updates and returns the dictionary of outlet streams.
        """
        pass

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """
        Default dynamic step falls back to steady-state evaluation,
        unless overridden with dynamic ODE holdup integration.
        """
        self.evaluate_steady_state(inlet_streams, outlet_streams)

    def compute_balance_audit(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, float]:
        """
        Audits mass and energy conservation across this block.
        Returns:
            mass_in_tph, mass_out_tph, mass_err_pct,
            heat_in_gjh, heat_out_gjh, heat_loss_gjh, energy_err_pct
        """
        mass_in = sum(s.mass_flow_tph for s in inlet_streams.values() if s is not None)
        mass_out = sum(s.mass_flow_tph for s in outlet_streams.values() if s is not None)
        mass_err = abs(mass_in - mass_out)
        mass_err_pct = (mass_err / max(1e-3, mass_in)) * 100.0 if mass_in > 0 else 0.0

        heat_in = sum(s.enthalpy_gjh for s in inlet_streams.values() if s is not None)
        heat_out = sum(s.enthalpy_gjh for s in outlet_streams.values() if s is not None)
        heat_loss = float(self.state.get("heat_loss_gjh", 0.0))
        heat_err = abs((heat_in) - (heat_out + heat_loss))
        energy_err_pct = (heat_err / max(1e-3, heat_in)) * 100.0 if heat_in > 0 else 0.0

        return {
            "mass_in_tph": round(mass_in, 3),
            "mass_out_tph": round(mass_out, 3),
            "mass_err_tph": round(mass_err, 3),
            "mass_err_pct": round(mass_err_pct, 2),
            "heat_in_gjh": round(heat_in, 3),
            "heat_out_gjh": round(heat_out, 3),
            "heat_loss_gjh": round(heat_loss, 3),
            "energy_err_pct": round(energy_err_pct, 2),
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns runtime state variables for HMI cards and OPC UA publishing."""
        return {
            "block_id": self.block_id,
            "name": self.name,
            "type": self.block_type,
            "state": self.state,
            "parameters": self.parameters,
        }

    def get_opc_tags(self) -> List[Dict[str, Any]]:
        """
        Auto-generates tag metadata for OPC UA node registration.
        """
        tags = []
        for state_key, val in self.state.items():
            if isinstance(val, (int, float, bool)):
                tags.append({
                    "tag_id": f"{self.block_id}_{state_key.upper()}",
                    "node_id": f"ns=2;s={self.block_id}_{state_key.upper()}",
                    "name": f"{self.name} {state_key.replace('_', ' ').title()}",
                    "category": self.category,
                    "unit": "",
                    "value": val,
                    "access": "RO",
                    "source": "opc_ua",
                })
        for param_key, val in self.parameters.items():
            if isinstance(val, (int, float)):
                tags.append({
                    "tag_id": f"{self.block_id}_SP_{param_key.upper()}",
                    "node_id": f"ns=2;s={self.block_id}_SP_{param_key.upper()}",
                    "name": f"{self.name} Setpoint {param_key.replace('_', ' ').title()}",
                    "category": self.category,
                    "unit": self.parameter_schema.get(param_key, {}).get("unit", ""),
                    "value": val,
                    "access": "RW",
                    "source": "opc_ua",
                })
        return tags

    def to_dict(self) -> Dict[str, Any]:
        """Serializes block to dictionary."""
        return {
            "id": self.block_id,
            "name": self.name,
            "type": self.block_type,
            "category": self.category,
            "position": self.position,
            "parameters": self.parameters,
            "state": self.state,
            "ports": {k: p.to_dict() for k, p in self.ports.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockBase":
        """Instantiates and configures block from dictionary."""
        inst = cls(
            block_id=data.get("id", data.get("block_id", "BLOCK_01")),
            name=data.get("name", ""),
            position=data.get("position", {"x": 100, "y": 100}),
            parameters=data.get("parameters", {}),
        )
        if "state" in data:
            inst.state.update(data["state"])
        if "ports" in data:
            for p_name, p_data in data["ports"].items():
                if p_name in inst.ports:
                    inst.ports[p_name].connected_stream_id = p_data.get("connected_stream_id")
        return inst
