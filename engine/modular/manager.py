"""
ModularEngineManager: Central coordinator managing active modular flowsheets,
solver runtime, file persistence, and OPC UA dynamic tag synchronization.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from .flowsheet_graph import FlowsheetGraph
from .solver import FlowsheetSolver
from .library import get_block_class, get_component_catalog
from .templates import get_template_manifest, load_template_graph, TEMPLATE_BUILDERS

logger = logging.getLogger("ModularEngineManager")


class ModularEngineManager:
    """
    Manages active modular flowsheet graphs, solves balances, coordinates dynamic steps,
    and synchronizes telemetry with Web HMI and OPC UA server.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "flowsheets",
        )
        os.makedirs(self.storage_dir, exist_ok=True)

        # Default to Kiln 3 Pyroprocessing Plant template
        self.active_graph: FlowsheetGraph = load_template_graph("kiln_3_pyroprocess")
        self.solver: FlowsheetSolver = FlowsheetSolver(self.active_graph)
        # Solve initial steady state
        self.solver.solve_steady_state()
        logger.info(f"Initialized ModularEngineManager with default graph '{self.active_graph.name}'")

    def get_component_catalog(self) -> List[Dict[str, Any]]:
        """Returns component palette schema catalog."""
        return get_component_catalog()

    def get_template_manifest(self) -> List[Dict[str, str]]:
        """Returns pre-built template metadata."""
        return get_template_manifest()

    def get_template_data(self, template_id: str) -> Dict[str, Any]:
        """Returns JSON graph for requested template ID with fully instantiated ports."""
        if template_id not in TEMPLATE_BUILDERS:
            raise KeyError(f"Template '{template_id}' not found.")
        graph = load_template_graph(template_id)
        return graph.to_dict()

    def load_graph_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces active flowsheet graph with user graph data."""
        self.active_graph = FlowsheetGraph.from_dict(data, block_factory=get_block_class)
        self.solver = FlowsheetSolver(self.active_graph)
        res = self.solver.solve_steady_state()
        logger.info(f"Loaded new flowsheet graph '{self.active_graph.name}' (Converged: {res['converged']})")
        return {
            "status": "success",
            "flowsheet_id": self.active_graph.flowsheet_id,
            "name": self.active_graph.name,
            "solve_result": res,
            "graph": self.active_graph.to_dict(),
        }

    def solve_graph_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Solves a flowsheet graph on-the-fly and synchronizes active graph and solver."""
        temp_graph = FlowsheetGraph.from_dict(data, block_factory=get_block_class)
        temp_solver = FlowsheetSolver(temp_graph)
        res = temp_solver.solve_steady_state()
        self.active_graph = temp_graph
        self.solver = temp_solver
        return {
            "status": "success",
            "solve_result": res,
            "graph": temp_graph.to_dict(),
        }

    def update_block_parameter(self, block_id: str, param_name: str, value: Any) -> Dict[str, Any]:
        """Updates a single block parameter on active flowsheet graph in real time and re-solves balances."""
        if block_id in self.active_graph.blocks:
            b = self.active_graph.blocks[block_id]
            # Support parameter name aliases for feeders
            if b.block_type in ("GravimetricFeeder", "FuelFeeder") and param_name in (
                "feed_rate_tph", "fuel_rate_tph", "feed_rate", "fuel_rate", "rate_tph", "rate"
            ):
                param_name = "nominal_rate_tph"
            b.set_parameter(param_name, value)
            if b.block_type in ("GravimetricFeeder", "FuelFeeder") and param_name == "nominal_rate_tph":
                try:
                    num_val = float(value)
                    b.state["actual_feed_rate_tph" if b.block_type == "GravimetricFeeder" else "actual_rate_tph"] = num_val
                    # Propagate to outgoing stream
                    for s in self.active_graph.get_block_outlets(block_id).values():
                        if s:
                            s.mass_flow_tph = num_val
                except Exception:
                    pass
            # Re-solve coupled steady state balances so downstream blocks react instantly
            solve_res = self.solver.solve_steady_state()
            audit = self.active_graph.audit_plant_conservation()
            return {
                "status": "success",
                "block_id": block_id,
                "param": param_name,
                "value": value,
                "solve_result": solve_res,
                "telemetry": self.solver.get_blocks_telemetry(),
                "stream_table": self.solver.get_stream_table(),
                "audit": audit,
            }
        return {"status": "error", "message": f"Block '{block_id}' not found"}

    def rename_block(self, old_block_id: str, new_block_id: str) -> Dict[str, Any]:
        """Renames a block in the active flowsheet and propagates to connections."""
        if not self.active_graph:
            return {"status": "skipped", "message": "No active graph", "old_id": old_block_id, "new_id": new_block_id}
        if old_block_id not in self.active_graph.blocks:
            # Block exists only on the UI canvas so far (synced on Solve/Deploy) - nothing to rename server-side.
            return {"status": "skipped", "message": f"Block '{old_block_id}' not in backend graph yet; will sync on next Solve/Deploy", "old_id": old_block_id, "new_id": new_block_id}
        try:
            self.active_graph.rename_block(old_block_id, new_block_id)
            return {"status": "success", "old_id": old_block_id, "new_id": new_block_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def step(self, dt: float = 0.5) -> Dict[str, Any]:
        """Advances dynamic simulation on active modular flowsheet."""
        step_res = self.solver.step(dt)
        return {
            "status": "success",
            "time_s": step_res["time_s"],
            "step_count": step_res["step_count"],
            "audit": step_res["audit"],
            "streams": self.solver.get_stream_table(),
            "telemetry": self.solver.get_blocks_telemetry(),
        }

    def get_active_flowsheet(self) -> Dict[str, Any]:
        """Returns active flowsheet graph including live stream states and equipment telemetry."""
        audit = self.active_graph.audit_plant_conservation()
        return {
            "flowsheet": self.active_graph.to_dict(),
            "audit": audit,
            "simulation_time_s": self.solver.simulation_time_s,
            "step_count": self.solver.step_count,
            "stream_table": self.solver.get_stream_table(),
            "telemetry": self.solver.get_blocks_telemetry(),
        }

    def save_to_file(self, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves a flowsheet JSON into the flowsheet storage directory."""
        if not filename.endswith(".json"):
            filename += ".json"
        safe_name = "".join(c for c in filename if c.isalnum() or c in ("-", "_", ".")).strip()
        filepath = os.path.join(self.storage_dir, safe_name)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved custom flowsheet to {filepath}")
        return {"status": "success", "filename": safe_name, "path": filepath}

    def list_saved_files(self) -> List[Dict[str, Any]]:
        """Lists all user-saved flowsheet JSON files."""
        files = []
        if os.path.exists(self.storage_dir):
            for fname in os.listdir(self.storage_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.storage_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            d = json.load(f)
                        files.append({
                            "filename": fname,
                            "name": d.get("name", fname),
                            "flowsheet_id": d.get("flowsheet_id", fname),
                            "blocks_count": len(d.get("components", [])),
                            "streams_count": len(d.get("connections", [])),
                        })
                    except Exception:
                        files.append({"filename": fname, "name": fname})
        return files

    def load_from_file(self, filename: str) -> Dict[str, Any]:
        """Loads a saved flowsheet JSON file into the active engine."""
        if not filename.endswith(".json"):
            filename += ".json"
        filepath = os.path.join(self.storage_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File '{filename}' not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.load_graph_data(data)

    def get_opc_tags(self) -> List[Dict[str, Any]]:
        """Collects all auto-generated OPC UA tags across all blocks in the active flowsheet."""
        tags = []
        for b in self.active_graph.blocks.values():
            tags.extend(b.get_opc_tags())
        return tags
