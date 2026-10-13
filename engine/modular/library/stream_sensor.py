"""
StreamSensor: Chemical Assay & Species Analyzer Component.
Exclusively measures chemical species and assay variables of connected process streams.
Tags are generated dynamically in the format: {ID}_{species}_pct
Only exposes species OPC UA tags when a stream is actively connected to the sensor component.
"""

from typing import Dict, List, Any, Optional
import copy

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class StreamSensor(BlockBase):
    """
    Process Stream Chemical Assay & Species Sensor.
    Monitors and publishes chemical species concentrations ({ID}_{SPECIES}_PCT)
    strictly when connected to an active process stream.
    """
    block_type = "StreamSensor"
    category = "Instrumentation"
    icon = "sensor"

    def _define_ports(self) -> List[Port]:
        return [
            Port(
                "in_stream",
                PortDirection.IN,
                StreamPhase.ANY,
                "Process stream to analyze for chemical species (any phase)",
                required=True,
            ),
            Port(
                "out_stream",
                PortDirection.OUT,
                StreamPhase.ANY,
                "Transparent stream continuation discharge (any phase)",
                required=False,
            ),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "sensor_technology": {
                "type": str,
                "default": "Online Cross-Belt / In-Situ Optical Assay",
                "label": "Sensor Technology",
            },
            "response_lag_s": {
                "type": float,
                "default": 2.0,
                "min": 0.1,
                "max": 60.0,
                "unit": "s",
                "label": "Assay Filter Lag",
            },
        }

    def initialize(self):
        # Empty by default: no tags exist until a stream is actively connected
        self.state = {}
        self.has_inlet_connection = False
        self.has_outlet_connection = False

    def _normalize_species_name(self, key: str) -> str:
        """Converts species key to standard clean format ending in _pct or _ppm."""
        s = str(key).lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        if s.endswith("%"):
            s = s[:-1] + "_pct"
        elif not (
            s.endswith("_pct")
            or s.endswith("_ppm")
            or s.endswith("_tph")
            or s.endswith("_kg")
            or s.endswith("_ratio")
            or s.endswith("_s")
        ):
            s = f"{s}_pct"
        return s

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_stream")
        out_stream = outlet_streams.get("out_stream")

        self.has_inlet_connection = in_stream is not None
        self.has_outlet_connection = out_stream is not None

        # Reset state dictionary: only species present in currently connected streams will be exposed
        new_state: Dict[str, float] = {}

        if not self.has_inlet_connection and not self.has_outlet_connection:
            self.state = {}
            return outlet_streams

        # 1. Inlet Stream Chemical Species Evaluation
        if in_stream:
            comp_in = in_stream.composition or {}
            for key, val in comp_in.items():
                if isinstance(val, (int, float)):
                    s_name = self._normalize_species_name(key)
                    val_float = round(float(val), 3)
                    new_state[s_name] = val_float
                    if self.has_outlet_connection:
                        new_state[f"{s_name}_in"] = val_float

        # 2. Outlet Stream 100% Transparent Pass-through (Zero Mass/Energy Impact)
        if out_stream:
            comp_in = copy.deepcopy(in_stream.composition) if in_stream else {}
            m_in = in_stream.mass_flow_tph if in_stream else 0.0
            t_in = in_stream.temperature_c if in_stream else 25.0
            p_in = in_stream.pressure_mbar if in_stream else 0.0

            out_stream.update_state(
                mass_flow_tph=m_in,
                temperature_c=t_in,
                pressure_mbar=p_in,
                composition=comp_in,
            )
            if in_stream:
                out_stream.enthalpy_gjh = in_stream.enthalpy_gjh
                out_stream.phase = in_stream.phase

            for key, val in comp_in.items():
                if isinstance(val, (int, float)):
                    s_name = self._normalize_species_name(key)
                    val_float = round(float(val), 3)
                    new_state[f"{s_name}_out"] = val_float
                    if not in_stream:
                        new_state[s_name] = val_float

        self.state = new_state
        return outlet_streams

    def compute_mass_energy_balance(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, float]:
        """
        Sensors are measurement instruments and are completely ignored in mass/energy balance audits.
        Always returns 0.0 mass and energy error.
        """
        in_s = inlet_streams.get("in_stream")
        m = in_s.mass_flow_tph if in_s else 0.0
        h = in_s.enthalpy_gjh if in_s else 0.0
        return {
            "mass_in_tph": round(m, 3),
            "mass_out_tph": round(m, 3),
            "mass_err_tph": 0.0,
            "mass_err_pct": 0.0,
            "heat_in_gjh": round(h, 3),
            "heat_out_gjh": round(h, 3),
            "heat_loss_gjh": 0.0,
            "energy_err_pct": 0.0,
        }

    compute_balance_audit = compute_mass_energy_balance

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic step simulating sensor response time and filter lag for species."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        lag_s = max(0.1, float(self.parameters.get("response_lag_s", 2.0)))

        for key in list(self.state.keys()):
            if key.startswith("dyn_"):
                continue
            val = self.state[key]
            if isinstance(val, (int, float)):
                dyn_key = f"dyn_{key}"
                cur_val = self.state.get(dyn_key, val)
                new_val = cur_val + (val - cur_val) * (dt / lag_s)
                self.state[dyn_key] = round(new_val, 3)
                self.state[key] = round(new_val, 3)

    def get_opc_tags(self) -> List[Dict[str, Any]]:
        """
        Auto-generates OPC UA tags STRICTLY for chemical species present in the connected stream.
        Format: {ID}_{SPECIES_NAME} (e.g. SENSOR_01_CACO3_PCT, SENSOR_01_SIO2_PCT).
        Excludes all general physical stream transport tags (flow, T, P, H, deltas, setpoints).
        Returns an EMPTY list when no stream is connected to the sensor.
        """
        if not self.has_inlet_connection and not self.has_outlet_connection:
            return []

        tags = []
        state_snapshot = list(self.state.copy().items())
        for state_key, val in state_snapshot:
            if not isinstance(val, (int, float)):
                continue
            if state_key.startswith("dyn_"):
                continue

            num_val = round(float(val), 3)
            tag_id = f"{self.block_id}_{state_key.upper()}"
            unit_str = "%" if "pct" in state_key else ("ppm" if "ppm" in state_key else "")

            tags.append({
                "tag_id": tag_id,
                "node_id": f"ns=2;s={tag_id}",
                "opc_node_id": f"ns=2;s={tag_id}",
                "name": f"{self.name} {state_key.replace('_', ' ').title()}",
                "category": "measurement",
                "equipment_category": self.category,
                "unit": unit_str,
                "value": num_val,
                "live_value": num_val,
                "access": "RO",
                "opc_direction": "read",
                "source": "opc_ua",
                "hmi_tag": f"{self.block_id}.{state_key}",
                "status": "RUNNING",
            })
        return tags
