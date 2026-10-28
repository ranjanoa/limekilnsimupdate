"""
Multi-Condition Safety Permissive & Emergency Trip Matrix.
Aggregates safety interlocks (e.g. ID Fan running, Hood Draft negative, Cooling Air OK).
Generates Master Permissive (to start equipment) and Master Trip.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class InterlockMatrix(BlockBase):
    """
    Multi-Condition Safety Permissive & Emergency Trip Matrix.
    Aggregates safety interlocks (e.g. ID Fan running, Hood Draft negative, Cooling Air OK).
    Generates Master Permissive (to start equipment) and Master Trip.
    """
    block_type = "InterlockMatrix"
    category = "Control / Binary"
    icon = "🔒"

    def _define_ports(self) -> List[Port]:
        return [
            Port("cond_1", PortDirection.IN, StreamPhase.BINARY, "Safety Interlock Condition 1", required=True),
            Port("cond_2", PortDirection.IN, StreamPhase.BINARY, "Safety Interlock Condition 2", required=False),
            Port("cond_3", PortDirection.IN, StreamPhase.BINARY, "Safety Interlock Condition 3", required=False),
            Port("cond_4", PortDirection.IN, StreamPhase.BINARY, "Safety Interlock Condition 4", required=False),
            Port("out_permissive", PortDirection.OUT, StreamPhase.BINARY, "Master Permissive OK (1=Safe to Run)", required=True),
            Port("out_trip", PortDirection.OUT, StreamPhase.BINARY, "Master Trip (1=Tripped)", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "logic_mode": {"type": str, "default": "ALL_REQUIRED", "label": "Evaluation Logic (ALL_REQUIRED/ANY_REQUIRED/MAJORITY_VOTE)"},
            "bypass_active": {"type": bool, "default": False, "label": "Manual Maintenance Bypass (1=Bypassed)"},
        }

    def initialize(self):
        self.state = {
            "cond_1": True,
            "cond_2": True,
            "cond_3": True,
            "cond_4": True,
            "permissive_ok": True,
            "trip_active": False,
            "bypassed": False,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        c1 = inlet_streams["cond_1"].binary_state if "cond_1" in inlet_streams and inlet_streams["cond_1"] else True
        c2 = inlet_streams["cond_2"].binary_state if "cond_2" in inlet_streams and inlet_streams["cond_2"] else True
        c3 = inlet_streams["cond_3"].binary_state if "cond_3" in inlet_streams and inlet_streams["cond_3"] else True
        c4 = inlet_streams["cond_4"].binary_state if "cond_4" in inlet_streams and inlet_streams["cond_4"] else True

        bypass = bool(self.parameters.get("bypass_active", False))
        mode = str(self.parameters.get("logic_mode", "ALL_REQUIRED")).upper()

        active_conds = [c1]
        if "cond_2" in inlet_streams and inlet_streams["cond_2"]:
            active_conds.append(c2)
        if "cond_3" in inlet_streams and inlet_streams["cond_3"]:
            active_conds.append(c3)
        if "cond_4" in inlet_streams and inlet_streams["cond_4"]:
            active_conds.append(c4)

        if bypass:
            permissive = True
        elif mode == "ANY_REQUIRED":
            permissive = any(active_conds)
        elif mode == "MAJORITY_VOTE":
            true_count = sum(1 for c in active_conds if c)
            permissive = (true_count > (len(active_conds) / 2))
        else:
            # ALL_REQUIRED
            permissive = all(active_conds)

        trip = not permissive

        self.state["cond_1"] = c1
        self.state["cond_2"] = c2
        self.state["cond_3"] = c3
        self.state["cond_4"] = c4
        self.state["permissive_ok"] = permissive
        self.state["trip_active"] = trip
        self.state["bypassed"] = bypass

        out_perm = outlet_streams.get("out_permissive")
        out_trip = outlet_streams.get("out_trip")

        if out_perm:
            out_perm.update_state(binary_state=permissive, signal_value=1.0 if permissive else 0.0)
        if out_trip:
            out_trip.update_state(binary_state=trip, signal_value=1.0 if trip else 0.0)

        return outlet_streams
