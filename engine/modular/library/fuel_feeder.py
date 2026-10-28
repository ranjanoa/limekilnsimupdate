"""
Solid/liquid or alternative fuel dosing system.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class FuelFeeder(BlockBase):
    """
    Solid/liquid or alternative fuel dosing system.
    """
    block_type = "FuelFeeder"
    category = "Feeding"
    icon = "flame"

    def _define_ports(self) -> List[Port]:
        return [
            Port("out_fuel", PortDirection.OUT, StreamPhase.FUEL, "Dosed fuel supply to burner/calciner", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "fuel_name": {"type": str, "default": "Petcoke", "label": "Fuel Grade"},
            "nominal_rate_tph": {"type": float, "default": 8.5, "min": 0.0, "max": 40.0, "unit": "t/h", "label": "Dosing Rate"},
            "lhv_mj_kg": {"type": float, "default": 31.4, "min": 10.0, "max": 50.0, "unit": "MJ/kg", "label": "Lower Heating Value"},
            "ash_pct": {"type": float, "default": 0.8, "min": 0.0, "max": 35.0, "unit": "%", "label": "Ash Content"},
            "moisture_pct": {"type": float, "default": 1.0, "min": 0.0, "max": 25.0, "unit": "%", "label": "Fuel Moisture"},
        }

    def initialize(self):
        rate = float(self.parameters.get("nominal_rate_tph", 8.5))
        lhv = float(self.parameters.get("lhv_mj_kg", 31.4))
        heat_mw = (rate * 1000.0 * lhv) / 3600.0
        self.state = {
            "actual_rate_tph": rate,
            "heat_input_mw": round(heat_mw, 2),
            "heat_input_gjh": round(rate * lhv, 2),
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        rate = float(self.parameters.get("nominal_rate_tph", 8.5))
        lhv = float(self.parameters.get("lhv_mj_kg", 31.4))
        heat_mw = (rate * 1000.0 * lhv) / 3600.0

        self.state["actual_rate_tph"] = rate
        self.state["heat_input_mw"] = round(heat_mw, 2)
        self.state["heat_input_gjh"] = round(rate * lhv, 2)

        out_stream = outlet_streams.get("out_fuel")
        if out_stream:
            out_stream.update_state(
                mass_flow_tph=rate,
                temperature_c=25.0,
                pressure_mbar=0.0,
                composition={
                    "fuel_name": self.parameters.get("fuel_name", "Petcoke"),
                    "lhv_mj_kg": lhv,
                    "ash_pct": float(self.parameters.get("ash_pct", 0.8)),
                    "moisture_pct": float(self.parameters.get("moisture_pct", 1.0)),
                },
            )
        return outlet_streams
