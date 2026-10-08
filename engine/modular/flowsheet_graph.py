"""
FlowsheetGraph: Directed graph representation of modular process units and streams.
Manages block connectivity, topological sorting, tear-stream loop identification,
serialization, and conservation audits.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import json
import logging

from .stream import ProcessStream, StreamPhase
from .block_base import BlockBase, PortDirection

logger = logging.getLogger("FlowsheetGraph")


class FlowsheetGraph:
    """
    Core directed graph representing an interconnected process flowsheet.
    """

    def __init__(
        self,
        flowsheet_id: str = "custom_flowsheet",
        name: str = "Custom Process Flowsheet",
        version: str = "2.0",
        description: str = "",
    ):
        self.flowsheet_id = flowsheet_id
        self.name = name
        self.version = version
        self.description = description

        self.blocks: Dict[str, BlockBase] = {}
        self.streams: Dict[int, ProcessStream] = {}
        self._next_stream_id: int = 1

    def add_block(self, block: BlockBase) -> BlockBase:
        """Adds a block instance to the graph."""
        if block.block_id in self.blocks:
            raise ValueError(f"Block with ID '{block.block_id}' already exists in graph.")
        self.blocks[block.block_id] = block
        return block

    def remove_block(self, block_id: str):
        """Removes a block and all associated input/output streams."""
        if block_id not in self.blocks:
            return

        # Find and disconnect all connected streams
        streams_to_remove = [
            sid for sid, stream in self.streams.items()
            if stream.from_block == block_id or stream.to_block == block_id
        ]
        for sid in streams_to_remove:
            self.disconnect_stream(sid)

        del self.blocks[block_id]

    def rename_block(self, old_block_id: str, new_block_id: str):
        """Renames a block and updates all connected streams and ports."""
        if old_block_id not in self.blocks:
            raise ValueError(f"Block '{old_block_id}' not found.")
        if new_block_id in self.blocks and new_block_id != old_block_id:
            raise ValueError(f"Block ID '{new_block_id}' already exists.")
        block = self.blocks.pop(old_block_id)
        block.block_id = new_block_id
        self.blocks[new_block_id] = block
        for stream in self.streams.values():
            if stream.from_block == old_block_id:
                stream.from_block = new_block_id
            if stream.to_block == old_block_id:
                stream.to_block = new_block_id

    def connect(
        self,
        from_block_id: str,
        from_port_name: str,
        to_block_id: str,
        to_port_name: str,
        name: str = "",
        stream_id: Optional[int] = None,
        phase: Optional[StreamPhase] = None,
    ) -> ProcessStream:
        """
        Creates a process stream connection between an output port and an input port.
        """
        if from_block_id not in self.blocks:
            raise ValueError(f"Source block '{from_block_id}' not found.")
        if to_block_id not in self.blocks:
            raise ValueError(f"Destination block '{to_block_id}' not found.")

        src_block = self.blocks[from_block_id]
        dst_block = self.blocks[to_block_id]

        if from_port_name not in src_block.ports:
            raise ValueError(f"Port '{from_port_name}' not found on source block '{from_block_id}'.")
        if to_port_name not in dst_block.ports:
            raise ValueError(f"Port '{to_port_name}' not found on target block '{to_block_id}'.")

        src_port = src_block.ports[from_port_name]
        dst_port = dst_block.ports[to_port_name]

        if src_port.direction != PortDirection.OUT:
            raise ValueError(f"Source port '{from_port_name}' on '{from_block_id}' must be an OUT port.")
        if dst_port.direction != PortDirection.IN:
            raise ValueError(f"Target port '{to_port_name}' on '{to_block_id}' must be an IN port.")

        # Disconnect any existing stream on the target port
        if dst_port.connected_stream_id is not None:
            self.disconnect_stream(dst_port.connected_stream_id)

        # Allocate Stream ID
        if stream_id is None:
            sid = self._next_stream_id
            self._next_stream_id += 1
        else:
            sid = stream_id
            if sid >= self._next_stream_id:
                self._next_stream_id = sid + 1

        stream_phase = phase or src_port.phase or dst_port.phase
        stream_name = name or f"{src_block.name} -> {dst_block.name}"

        stream = ProcessStream(
            stream_id=sid,
            name=stream_name,
            from_block=from_block_id,
            from_port=from_port_name,
            to_block=to_block_id,
            to_port=to_port_name,
            phase=stream_phase,
        )

        self.streams[sid] = stream
        src_port.connected_stream_id = sid
        dst_port.connected_stream_id = sid

        return stream

    def disconnect_stream(self, stream_id: int):
        """Removes a stream and unbinds block ports."""
        if stream_id not in self.streams:
            return

        stream = self.streams[stream_id]
        if stream.from_block in self.blocks:
            src_block = self.blocks[stream.from_block]
            if stream.from_port in src_block.ports:
                src_block.ports[stream.from_port].connected_stream_id = None

        if stream.to_block in self.blocks:
            dst_block = self.blocks[stream.to_block]
            if stream.to_port in dst_block.ports:
                dst_block.ports[stream.to_port].connected_stream_id = None

        del self.streams[stream_id]

    def get_block_inlets(self, block_id: str) -> Dict[str, ProcessStream]:
        """Returns map of {port_name: ProcessStream} for inlet ports."""
        block = self.blocks.get(block_id)
        if not block:
            return {}
        result = {}
        for p_name, p in block.ports.items():
            if p.direction == PortDirection.IN and p.connected_stream_id in self.streams:
                result[p_name] = self.streams[p.connected_stream_id]
            elif p.direction == PortDirection.IN:
                result[p_name] = None
        return result

    def get_block_outlets(self, block_id: str) -> Dict[str, ProcessStream]:
        """Returns map of {port_name: ProcessStream} for outlet ports."""
        block = self.blocks.get(block_id)
        if not block:
            return {}
        result = {}
        for p_name, p in block.ports.items():
            if p.direction == PortDirection.OUT and p.connected_stream_id in self.streams:
                result[p_name] = self.streams[p.connected_stream_id]
            elif p.direction == PortDirection.OUT:
                result[p_name] = None
        return result

    def get_upstream_blocks(self, block_id: str) -> List[str]:
        """Finds all direct predecessor block IDs."""
        inlets = self.get_block_inlets(block_id)
        return list({s.from_block for s in inlets.values() if s is not None and s.from_block})

    def get_downstream_blocks(self, block_id: str) -> List[str]:
        """Finds all direct successor block IDs."""
        outlets = self.get_block_outlets(block_id)
        return list({s.to_block for s in outlets.values() if s is not None and s.to_block})

    def topological_sort(self) -> Tuple[List[str], List[int]]:
        """
        Computes computational sequence using modified Tarjan/Kahn algorithm.
        Breaks feedback cycles by identifying tear streams (e.g. recycle loops).
        Returns:
            execution_order: List of block_ids
            tear_stream_ids: List of stream_ids chosen as tear streams
        """
        adj: Dict[str, Set[str]] = {b_id: set() for b_id in self.blocks}
        stream_map: Dict[Tuple[str, str], List[int]] = {}

        for sid, stream in self.streams.items():
            u, v = stream.from_block, stream.to_block
            if u in self.blocks and v in self.blocks:
                adj[u].add(v)
                stream_map.setdefault((u, v), []).append(sid)

        # Detect feedback edges via Depth First Search
        visited: Dict[str, int] = {b_id: 0 for b_id in self.blocks}  # 0=unvisited, 1=visiting, 2=visited
        tear_streams: List[int] = []
        feedback_edges: Set[Tuple[str, str]] = set()

        def dfs(u: str):
            visited[u] = 1
            for v in list(adj[u]):
                if (u, v) in feedback_edges:
                    continue
                if visited[v] == 1:
                    # Found cycle: mark u -> v as feedback edge
                    feedback_edges.add((u, v))
                    adj[u].remove(v)
                    if (u, v) in stream_map:
                        tear_streams.extend(stream_map[(u, v)])
                elif visited[v] == 0:
                    dfs(v)
            visited[u] = 2

        for b_id in self.blocks:
            if visited[b_id] == 0:
                dfs(b_id)

        # Now compute Kahn's topological sort on DAG with feedback edges removed
        in_degree: Dict[str, int] = {b_id: 0 for b_id in self.blocks}
        for u, neighbors in adj.items():
            for v in neighbors:
                in_degree[v] = in_degree.get(v, 0) + 1

        queue = [b for b, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            # Deterministic sorting
            queue.sort()
            curr = queue.pop(0)
            order.append(curr)

            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append any remaining disconnected nodes
        for b in self.blocks:
            if b not in order:
                order.append(b)

        return order, tear_streams

    def validate(self) -> Dict[str, Any]:
        """
        Validates graph integrity, identifying missing connections or phase mismatches.
        """
        errors = []
        warnings = []

        for b_id, block in self.blocks.items():
            for p_name, port in block.ports.items():
                if port.required and port.connected_stream_id is None:
                    if port.direction == PortDirection.IN:
                        warnings.append(f"Block '{b_id}': Input port '{p_name}' is not connected.")

        for sid, stream in self.streams.items():
            if stream.from_block not in self.blocks:
                errors.append(f"Stream {sid}: Source block '{stream.from_block}' does not exist.")
            if stream.to_block not in self.blocks:
                errors.append(f"Stream {sid}: Target block '{stream.to_block}' does not exist.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "block_count": len(self.blocks),
            "stream_count": len(self.streams),
        }

    def audit_plant_conservation(self) -> Dict[str, float]:
        """
        Calculates global mass and heat conservation across the entire flowsheet boundaries.
        Boundary inflows:
          - Feeders (raw meal, fuels)
          - Ambient cooling air introduced into cooler or other units
          - Any stream from an external source
        Boundary outflows:
          - Final products directed into silos or storage (clinker)
          - Flue gas exiting ID fan stacks
          - Excess cooler vent air to baghouse/atmosphere
          - Any unconnected block outlet streams
        """
        total_inflow_tph = 0.0
        total_outflow_tph = 0.0
        total_heat_in_gjh = 0.0
        total_heat_out_gjh = 0.0
        total_heat_loss_gjh = 0.0

        for b_id, b in self.blocks.items():
            # 1. Feeder inputs
            if b.block_type in ("GravimetricFeeder", "FuelFeeder"):
                for s in self.get_block_outlets(b_id).values():
                    if s:
                        total_inflow_tph += s.mass_flow_tph
                        total_heat_in_gjh += s.enthalpy_gjh
            elif b.block_type == "GrateCooler":
                # Cooling air from ambient atmosphere
                cooling_air_tph = float(b.parameters.get("cooling_air_total_tph", 348.5))
                total_inflow_tph += cooling_air_tph
                # Ambient air enthalpy ~ 0.24 * 25C * 4.184 / 1000 GJ/t ~ 0.025 GJ/t
                total_heat_in_gjh += cooling_air_tph * 0.025

            # Sum up heat losses across equipment shells and casing
            total_heat_loss_gjh += float(b.state.get("heat_loss_gjh", 0.0))

            # 2. Outflows: check terminal units or unconnected outlets
            if b.block_type == "SiloStorage":
                # Stored product (e.g. clinker)
                for s in self.get_block_inlets(b_id).values():
                    if s:
                        total_outflow_tph += s.mass_flow_tph
                        total_heat_out_gjh += s.enthalpy_gjh
            elif b.block_type == "IDFan":
                # Exhaust stack flue gas
                for s in self.get_block_inlets(b_id).values():
                    if s:
                        total_outflow_tph += s.mass_flow_tph
                        total_heat_out_gjh += s.enthalpy_gjh
            elif b.block_type == "GrateCooler":
                # Cooler vent air to atmosphere (if unconnected or terminal)
                outlets = self.get_block_outlets(b_id)
                vent_s = outlets.get("out_vent_air")
                if vent_s and (not vent_s.to_block or vent_s.to_block not in self.blocks):
                    total_outflow_tph += vent_s.mass_flow_tph
                    total_heat_out_gjh += vent_s.enthalpy_gjh
                elif not vent_s:
                    # Unconnected vent port exhausts directly to atmosphere
                    m_air_tot = float(b.parameters.get("cooling_air_total_tph", 348.5))
                    sec_pct = float(b.parameters.get("secondary_air_split_pct", 24.2)) / 100.0
                    tert_pct = float(b.parameters.get("tertiary_air_split_pct", 36.8)) / 100.0
                    vent_pct = max(0.0, 1.0 - (sec_pct + tert_pct))
                    m_vent_tph = m_air_tot * vent_pct
                    t_vent_c = float(b.state.get("cooler_vent_temp_c", 260.0))
                    total_outflow_tph += m_vent_tph
                    total_heat_out_gjh += m_vent_tph * 0.26 * 4.184 / 1000.0 * max(0.0, t_vent_c - 25.0)

                # Check if tertiary air is unconnected (e.g. standalone lime kiln without calciner)
                tert_s = outlets.get("out_tertiary_air")
                if not tert_s or (tert_s.to_block and tert_s.to_block not in self.blocks):
                    m_air_tot = float(b.parameters.get("cooling_air_total_tph", 348.5))
                    tert_pct = float(b.parameters.get("tertiary_air_split_pct", 36.8)) / 100.0
                    if tert_pct > 0.0:
                        m_tert_tph = m_air_tot * tert_pct
                        t_tert_c = float(b.state.get("tertiary_air_temp_c", 850.0))
                        total_outflow_tph += m_tert_tph
                        total_heat_out_gjh += m_tert_tph * 0.26 * 4.184 / 1000.0 * max(0.0, t_tert_c - 25.0)

        # Account for streams exiting graph
        for s in self.streams.values():
            if s.to_block not in self.blocks and s.from_block in self.blocks:
                total_outflow_tph += s.mass_flow_tph
                total_heat_out_gjh += s.enthalpy_gjh

        mass_err = abs(total_inflow_tph - total_outflow_tph)
        closure_pct = 100.0 - ((mass_err / max(1.0, total_inflow_tph)) * 100.0) if total_inflow_tph > 0 else 100.0

        return {
            "mass_in_tph": round(total_inflow_tph, 2),
            "mass_out_tph": round(total_outflow_tph, 2),
            "mass_err_tph": round(mass_err, 2),
            "mass_closure_pct": round(max(0.0, min(100.0, closure_pct)), 2),
            "heat_in_gjh": round(total_heat_in_gjh, 2),
            "heat_out_gjh": round(total_heat_out_gjh, 2),
            "heat_loss_gjh": round(total_heat_loss_gjh, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes flowsheet graph into standard JSON dictionary."""
        return {
            "flowsheet_id": self.flowsheet_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "components": [b.to_dict() for b in self.blocks.values()],
            "connections": [
                {
                    "stream_id": s.stream_id,
                    "name": s.name,
                    "source": {"block": s.from_block, "port": s.from_port},
                    "target": {"block": s.to_block, "port": s.to_port},
                    "phase": s.phase.value,
                    "mass_flow_tph": round(s.mass_flow_tph, 3),
                    "volume_flow_nm3h": round(s.volume_flow_nm3h, 1) if s.volume_flow_nm3h is not None else None,
                    "temperature_c": round(s.temperature_c, 2),
                    "pressure_mbar": round(s.pressure_mbar, 2),
                    "enthalpy_gjh": round(s.enthalpy_gjh, 3),
                    "composition": s.composition,
                }
                for s in self.streams.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], block_factory: Any) -> "FlowsheetGraph":
        """
        Reconstructs a flowsheet graph from dictionary using a block factory function/registry.
        """
        graph = cls(
            flowsheet_id=data.get("flowsheet_id", "custom_flowsheet"),
            name=data.get("name", "Custom Flowsheet"),
            version=data.get("version", "2.0"),
            description=data.get("description", ""),
        )

        # 1. Instantiate blocks
        for comp_data in data.get("components", []):
            b_type = comp_data.get("type")
            b_class = block_factory(b_type) if callable(block_factory) else None
            if b_class:
                block_inst = b_class.from_dict(comp_data)
                graph.add_block(block_inst)
            else:
                logger.warning(f"Unknown block type: {b_type}")

        # 2. Reconnect streams
        for conn_data in data.get("connections", []):
            src = conn_data.get("source", {})
            tgt = conn_data.get("target", {})
            sid = conn_data.get("stream_id")
            s_name = conn_data.get("name", "")
            s_phase = conn_data.get("phase")

            if src.get("block") in graph.blocks and tgt.get("block") in graph.blocks:
                stream = graph.connect(
                    from_block_id=src["block"],
                    from_port_name=src["port"],
                    to_block_id=tgt["block"],
                    to_port_name=tgt["port"],
                    name=s_name,
                    stream_id=sid,
                    phase=s_phase,
                )
                # Restore stream dynamic values if present
                stream.update_state(
                    mass_flow_tph=conn_data.get("mass_flow_tph"),
                    temperature_c=conn_data.get("temperature_c"),
                    pressure_mbar=conn_data.get("pressure_mbar"),
                    composition=conn_data.get("composition"),
                    volume_flow_nm3h=conn_data.get("volume_flow_nm3h"),
                )

        return graph
