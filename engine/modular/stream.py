"""
ProcessStream: Thermodynamic process stream carrying mass, species composition,
thermal enthalpy, pressure, and volumetric flow between unit operation blocks.
"""

from enum import Enum
from typing import Dict, Any, Optional
import copy


class StreamPhase(str, Enum):
    SOLID = "SOLID"
    GAS = "GAS"
    FUEL = "FUEL"
    AIR = "AIR"
    LIQUID = "LIQUID"


class ProcessStream:
    """
    Thermodynamic Process Stream representing material and energy transport
    between two unit operation ports.
    """

    def __init__(
        self,
        stream_id: int,
        name: str = "",
        from_block: str = "",
        from_port: str = "",
        to_block: str = "",
        to_port: str = "",
        phase: StreamPhase = StreamPhase.SOLID,
        mass_flow_tph: float = 0.0,
        volume_flow_nm3h: Optional[float] = None,
        temperature_c: float = 20.0,
        pressure_mbar: float = 0.0,
        enthalpy_gjh: Optional[float] = None,
        composition: Optional[Dict[str, float]] = None,
    ):
        self.stream_id = stream_id
        self.name = name or f"Stream_{stream_id}"
        self.from_block = from_block
        self.from_port = from_port
        self.to_block = to_block
        self.to_port = to_port
        self.phase = StreamPhase(phase) if isinstance(phase, str) else phase
        self.mass_flow_tph = float(mass_flow_tph)
        self.temperature_c = float(temperature_c)
        self.pressure_mbar = float(pressure_mbar)
        self.composition = composition or {}

        # Derived thermodynamic quantities
        if volume_flow_nm3h is not None:
            self.volume_flow_nm3h = float(volume_flow_nm3h)
        else:
            self.volume_flow_nm3h = self._estimate_volume_flow()

        if enthalpy_gjh is not None:
            self.enthalpy_gjh = float(enthalpy_gjh)
        else:
            self.enthalpy_gjh = self.compute_enthalpy()

    def get_heat_capacity_kcal_kg_c(self) -> float:
        """
        Calculates specific heat capacity Cp [kcal/(kg*C)] as a function of phase,
        temperature and composition.
        """
        t = self.temperature_c
        if self.phase == StreamPhase.SOLID:
            # Raw meal / clinker temperature dependent heat capacity
            # Cp ~ 0.18 + 0.00007 * T (kcal/kg*C)
            return round(max(0.18, 0.20 + 0.00005 * t), 4)
        elif self.phase in (StreamPhase.GAS, StreamPhase.AIR):
            # Flue gas / air Cp ~ 0.24 + 0.00003 * T
            return round(max(0.24, 0.242 + 0.000035 * t), 4)
        elif self.phase == StreamPhase.FUEL:
            # Solid/liquid fuel Cp
            return 0.28
        else:
            return 0.25

    def compute_enthalpy(self) -> float:
        """
        Computes sensible and chemical enthalpy rate [GJ/h].
        H_dot = m_dot [t/h] * Cp [kcal/(kg*C)] * (T_c + 273.15) [K] * 4.184e-3 [GJ/kcal]
        For fuels, chemical LHV enthalpy is added.
        """
        cp = self.get_heat_capacity_kcal_kg_c()
        # Sensible thermal enthalpy
        h_sensible = self.mass_flow_tph * cp * (self.temperature_c + 273.15) * 4.184 / 1000.0

        # Chemical energy for fuel streams
        h_chem = 0.0
        if self.phase == StreamPhase.FUEL:
            lhv_mj_kg = self.composition.get("lhv_mj_kg", 25.0)
            # 1 t = 1000 kg, 1 MJ = 1e-3 GJ -> 1 t * 1 MJ/kg = 1 GJ
            h_chem = self.mass_flow_tph * (lhv_mj_kg * 1.0)

        self.enthalpy_gjh = round(h_sensible + h_chem, 3)
        return self.enthalpy_gjh

    def _estimate_volume_flow(self) -> Optional[float]:
        """
        Estimates standard volumetric flow [Nm3/h] for gaseous and air phases.
        Standard density rho_0 ~ 1.293 kg/Nm3 for air, ~ 1.35 kg/Nm3 for kiln flue gas.
        """
        if self.phase == StreamPhase.AIR:
            rho_0 = 1.293  # kg/Nm3
            return round((self.mass_flow_tph * 1000.0) / rho_0, 1)
        elif self.phase == StreamPhase.GAS:
            rho_0 = 1.34  # kg/Nm3
            return round((self.mass_flow_tph * 1000.0) / rho_0, 1)
        return None

    def update_state(
        self,
        mass_flow_tph: Optional[float] = None,
        temperature_c: Optional[float] = None,
        pressure_mbar: Optional[float] = None,
        composition: Optional[Dict[str, float]] = None,
        volume_flow_nm3h: Optional[float] = None,
    ):
        """Updates stream physical state and recalculates thermodynamic properties."""
        if mass_flow_tph is not None:
            self.mass_flow_tph = float(mass_flow_tph)
        if temperature_c is not None:
            self.temperature_c = float(temperature_c)
        if pressure_mbar is not None:
            self.pressure_mbar = float(pressure_mbar)
        if composition is not None:
            self.composition = composition
        if volume_flow_nm3h is not None:
            self.volume_flow_nm3h = float(volume_flow_nm3h)
        else:
            self.volume_flow_nm3h = self._estimate_volume_flow()

        self.compute_enthalpy()

    def clone(self, new_id: Optional[int] = None) -> "ProcessStream":
        """Creates a deep copy of this stream."""
        return ProcessStream(
            stream_id=new_id if new_id is not None else self.stream_id,
            name=self.name,
            from_block=self.from_block,
            from_port=self.from_port,
            to_block=self.to_block,
            to_port=self.to_port,
            phase=self.phase,
            mass_flow_tph=self.mass_flow_tph,
            volume_flow_nm3h=self.volume_flow_nm3h,
            temperature_c=self.temperature_c,
            pressure_mbar=self.pressure_mbar,
            enthalpy_gjh=self.enthalpy_gjh,
            composition=copy.deepcopy(self.composition),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes stream to dictionary."""
        return {
            "stream_id": self.stream_id,
            "name": self.name,
            "from_node": self.from_block,
            "from_port": self.from_port,
            "to_node": self.to_block,
            "to_port": self.to_port,
            "phase": self.phase.value,
            "mass_flow_tph": round(self.mass_flow_tph, 3),
            "volume_flow_nm3h": round(self.volume_flow_nm3h, 1) if self.volume_flow_nm3h is not None else None,
            "temperature_c": round(self.temperature_c, 2),
            "pressure_mbar": round(self.pressure_mbar, 2),
            "enthalpy_gjh": round(self.enthalpy_gjh, 3),
            "composition": self.composition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessStream":
        """Deserializes stream from dictionary."""
        return cls(
            stream_id=data.get("stream_id", 0),
            name=data.get("name", ""),
            from_block=data.get("from_node", data.get("from_block", "")),
            from_port=data.get("from_port", ""),
            to_block=data.get("to_node", data.get("to_block", "")),
            to_port=data.get("to_port", ""),
            phase=data.get("phase", StreamPhase.SOLID.value),
            mass_flow_tph=data.get("mass_flow_tph", 0.0),
            volume_flow_nm3h=data.get("volume_flow_nm3h"),
            temperature_c=data.get("temperature_c", 20.0),
            pressure_mbar=data.get("pressure_mbar", 0.0),
            enthalpy_gjh=data.get("enthalpy_gjh"),
            composition=data.get("composition", {}),
        )
