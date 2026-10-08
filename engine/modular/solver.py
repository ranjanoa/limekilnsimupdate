"""
FlowsheetSolver: Sequential-modular steady-state solver with Wegstein loop acceleration
and dynamic ODE time-stepping integrator for modular process flowsheets.
"""

from typing import Dict, List, Tuple, Any, Optional
import copy
import logging

from .stream import ProcessStream
from .block_base import BlockBase
from .flowsheet_graph import FlowsheetGraph

logger = logging.getLogger("FlowsheetSolver")


class FlowsheetSolver:
    """
    Simulation Engine Solver for arbitrary flowsheet graphs.
    Provides steady-state iterative solving with Wegstein acceleration
    and real-time dynamic time integration.
    """

    def __init__(
        self,
        graph: FlowsheetGraph,
        tolerance: float = 1e-4,
        max_iterations: int = 50,
        wegstein_bound: float = 2.0,
    ):
        self.graph = graph
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.wegstein_bound = wegstein_bound

        self.simulation_time_s: float = 0.0
        self.step_count: int = 0
        self.is_running: bool = False

    def solve_steady_state(self) -> Dict[str, Any]:
        """
        Executes sequential-modular steady-state solver.
        Identifies recycle loops, accelerates tear streams with Wegstein method,
        and converges mass and thermal balances across the entire plant.
        """
        exec_order, tear_stream_ids = self.graph.topological_sort()

        converged = False
        iteration = 0
        max_residual = 0.0

        # Previous iteration values for Wegstein acceleration
        # Maps stream_id -> (prev_x, prev_fx)
        history: Dict[int, Dict[str, Tuple[float, float]]] = {}

        for it in range(self.max_iterations):
            iteration = it + 1
            max_residual = 0.0

            # Store snapshot of tear streams before evaluating blocks
            tear_snapshot: Dict[int, Dict[str, float]] = {}
            for sid in tear_stream_ids:
                s = self.graph.streams.get(sid)
                if s:
                    tear_snapshot[sid] = {
                        "mass": s.mass_flow_tph,
                        "temp": s.temperature_c,
                    }

            # Evaluate blocks in topological sequence
            for b_id in exec_order:
                block = self.graph.blocks.get(b_id)
                if not block:
                    continue
                inlets = self.graph.get_block_inlets(b_id)
                outlets = self.graph.get_block_outlets(b_id)
                block.evaluate_steady_state(inlets, outlets)

            if not tear_stream_ids:
                # Pure feed-forward acyclic flowsheet converges in 1 pass
                converged = True
                break

            # Convergence and Wegstein update for tear streams
            for sid in tear_stream_ids:
                s = self.graph.streams.get(sid)
                if not s or sid not in tear_snapshot:
                    continue

                x_curr = tear_snapshot[sid]["mass"]
                fx_curr = s.mass_flow_tph
                t_curr = tear_snapshot[sid]["temp"]
                ft_curr = s.temperature_c

                res_m = abs(fx_curr - x_curr) / max(1.0, abs(x_curr))
                res_t = abs(ft_curr - t_curr) / max(1.0, abs(t_curr))
                max_residual = max(max_residual, res_m, res_t)

                # Wegstein update for mass flow
                if sid in history and "mass" in history[sid]:
                    x_prev, fx_prev = history[sid]["mass"]
                    denom = (x_curr - x_prev)
                    if abs(denom) > 1e-6:
                        slope_s = (fx_curr - fx_prev) / denom
                        if abs(slope_s - 1.0) > 1e-4:
                            q = slope_s / (slope_s - 1.0)
                            # Bound Wegstein q parameter to prevent oscillation
                            q = max(-self.wegstein_bound, min(0.0, q))
                            new_x = (1.0 - q) * fx_curr + q * x_curr
                        else:
                            new_x = 0.5 * (x_curr + fx_curr)
                    else:
                        new_x = 0.5 * (x_curr + fx_curr)
                else:
                    new_x = 0.5 * (x_curr + fx_curr)

                # Update history
                history.setdefault(sid, {})["mass"] = (x_curr, fx_curr)
                s.update_state(mass_flow_tph=max(0.0, new_x))

            if max_residual < self.tolerance:
                converged = True
                break

        # Final audit of plant mass and heat balances
        audit = self.graph.audit_plant_conservation()

        return {
            "converged": converged,
            "iterations": iteration,
            "max_residual": round(max_residual, 6),
            "tear_streams_count": len(tear_stream_ids),
            "execution_order": exec_order,
            "audit": audit,
        }

    def step(self, dt: float = 0.5) -> Dict[str, Any]:
        """
        Advances dynamic simulation by timestep dt seconds.
        Integrates states across all blocks and propagates streams.
        """
        exec_order, _ = self.graph.topological_sort()

        for b_id in exec_order:
            block = self.graph.blocks.get(b_id)
            if not block:
                continue
            inlets = self.graph.get_block_inlets(b_id)
            outlets = self.graph.get_block_outlets(b_id)
            block.step(dt, inlets, outlets)

        self.simulation_time_s += dt
        self.step_count += 1

        audit = self.graph.audit_plant_conservation()
        return {
            "time_s": round(self.simulation_time_s, 2),
            "step_count": self.step_count,
            "audit": audit,
        }

    def get_stream_table(self) -> List[Dict[str, Any]]:
        """Returns tabular view of all streams for stream inspector table."""
        table = []
        for sid in sorted(self.graph.streams.keys()):
            s = self.graph.streams[sid]
            table.append(s.to_dict())
        return table

    def get_blocks_telemetry(self) -> Dict[str, Any]:
        """Returns live state dictionary of all blocks."""
        return {b_id: b.get_telemetry() for b_id, b in self.graph.blocks.items()}
