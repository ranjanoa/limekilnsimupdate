"""
Feeder & Storage Blocks:
- GravimetricFeeder: Raw meal and solid material continuous gravimetric dosing
- FuelFeeder: Solid, liquid, or alternative fuel dosing with net calorific value
- SiloStorage: Storage bin with level calculation and buffer lag
"""

from typing import Dict, List, Any
import math

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class GravimetricFeeder(BlockBase):
    """
    Continuous gravimetric loss-in-weight feeder with dynamic lag.
    """
    block_type = "GravimetricFeeder"
    category = "Feeding"
    icon = "feed-belt"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_material", PortDirection.IN, StreamPhase.SOLID, "Optional upstream silo feed", required=False),
            Port("out_solid", PortDirection.OUT, StreamPhase.SOLID, "Controlled raw meal flow", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "nominal_rate_tph": {"type": float, "default": 280.0, "min": 0.0, "max": 1000.0, "unit": "t/h", "label": "Feed Rate Setpoint"},
            "time_constant_s": {"type": float, "default": 1.5, "min": 0.1, "max": 30.0, "unit": "s", "label": "Feeder Response Lag"},
            "temperature_c": {"type": float, "default": 60.0, "min": 10.0, "max": 150.0, "unit": "°C", "label": "Feed Temperature"},
            "moisture_pct": {"type": float, "default": 0.8, "min": 0.0, "max": 15.0, "unit": "%", "label": "Moisture Content"},
            "caco3_pct": {"type": float, "default": 76.85, "min": 40.0, "max": 100.0, "unit": "%", "label": "CaCO3 (Limestone Purity)"},
            "mgco3_pct": {"type": float, "default": 2.15, "min": 0.0, "max": 30.0, "unit": "%", "label": "MgCO3 (Magnesite)"},
            "sio2_pct": {"type": float, "default": 13.50, "min": 0.1, "max": 40.0, "unit": "%", "label": "SiO2 (Silica)"},
            "al2o3_pct": {"type": float, "default": 3.45, "min": 0.1, "max": 20.0, "unit": "%", "label": "Al2O3 (Alumina)"},
            "fe2o3_pct": {"type": float, "default": 2.10, "min": 0.1, "max": 15.0, "unit": "%", "label": "Fe2O3 (Iron Oxide)"},
        }

    def initialize(self):
        sp = self.parameters.get("nominal_rate_tph", 280.0)
        caco3 = float(self.parameters.get("caco3_pct", 76.85))
        mgco3 = float(self.parameters.get("mgco3_pct", 2.15))
        sio2 = float(self.parameters.get("sio2_pct", 13.50))
        al2o3 = float(self.parameters.get("al2o3_pct", 3.45))
        fe2o3 = float(self.parameters.get("fe2o3_pct", 2.10))
        loi = caco3 * 0.43971 + mgco3 * 0.52197
        cao_eq = caco3 * (56.08 / 100.09)
        denom_lsf = 2.8 * sio2 + 1.2 * al2o3 + 0.65 * fe2o3
        lsf = (cao_eq / denom_lsf * 100.0) if denom_lsf > 0 else 0.0

        self.state = {
            "actual_feed_rate_tph": float(sp),
            "accumulated_tonnage_t": 0.0,
            "feeder_status": "RUNNING",
            "caco3_pct": round(caco3, 2),
            "loi_pct": round(loi, 2),
            "lsf": round(lsf, 1),
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        rate = float(self.parameters.get("nominal_rate_tph", 280.0))
        temp = float(self.parameters.get("temperature_c", 60.0))
        moist = float(self.parameters.get("moisture_pct", 0.8))
        caco3 = float(self.parameters.get("caco3_pct", 76.85))
        mgco3 = float(self.parameters.get("mgco3_pct", 2.15))
        sio2 = float(self.parameters.get("sio2_pct", 13.50))
        al2o3 = float(self.parameters.get("al2o3_pct", 3.45))
        fe2o3 = float(self.parameters.get("fe2o3_pct", 2.10))

        # Optional upstream silo/material stream composition override
        in_mat = inlet_streams.get("in_material")
        if in_mat and in_mat.composition:
            caco3 = float(in_mat.composition.get("CaCO3_pct", caco3))
            mgco3 = float(in_mat.composition.get("MgCO3_pct", mgco3))
            sio2 = float(in_mat.composition.get("SiO2_pct", sio2))
            al2o3 = float(in_mat.composition.get("Al2O3_pct", al2o3))
            fe2o3 = float(in_mat.composition.get("Fe2O3_pct", fe2o3))
            moist = float(in_mat.composition.get("Moisture_pct", moist))

        loi = caco3 * 0.43971 + mgco3 * 0.52197
        cao_eq = caco3 * (56.08 / 100.09)
        denom_lsf = 2.8 * sio2 + 1.2 * al2o3 + 0.65 * fe2o3
        lsf = (cao_eq / denom_lsf * 100.0) if denom_lsf > 0 else 0.0

        self.state["actual_feed_rate_tph"] = rate
        self.state["caco3_pct"] = round(caco3, 2)
        self.state["loi_pct"] = round(loi, 2)
        self.state["lsf"] = round(lsf, 1)

        out_stream = outlet_streams.get("out_solid")
        if out_stream:
            out_stream.update_state(
                mass_flow_tph=rate,
                temperature_c=temp,
                pressure_mbar=0.0,
                composition={
                    "CaCO3_pct": round(caco3, 2),
                    "MgCO3_pct": round(mgco3, 2),
                    "SiO2_pct": round(sio2, 2),
                    "Al2O3_pct": round(al2o3, 2),
                    "Fe2O3_pct": round(fe2o3, 2),
                    "Moisture_pct": round(moist, 2),
                    "LOI_pct": round(loi, 2),
                },
            )
        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        target = float(self.parameters.get("nominal_rate_tph", 280.0))
        tau = max(0.1, float(self.parameters.get("time_constant_s", 1.5)))
        current = float(self.state.get("actual_feed_rate_tph", target))

        # First-order lag response
        alpha = 1.0 - math.exp(-dt / tau)
        new_rate = current + alpha * (target - current)
        self.state["actual_feed_rate_tph"] = round(new_rate, 2)
        self.state["accumulated_tonnage_t"] += (new_rate * dt / 3600.0)

        out_stream = outlet_streams.get("out_solid")
        if out_stream:
            temp = float(self.parameters.get("temperature_c", 60.0))
            out_stream.update_state(
                mass_flow_tph=new_rate,
                temperature_c=temp,
                pressure_mbar=0.0,
            )


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


class SiloStorage(BlockBase):
    """
    Storage silo or meal surge bin.
    """
    block_type = "SiloStorage"
    category = "Feeding"
    icon = "database"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_solid", PortDirection.IN, StreamPhase.SOLID, "Inlet material from elevator", required=True),
            Port("out_solid", PortDirection.OUT, StreamPhase.SOLID, "Discharge to downstream process", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "capacity_tons": {"type": float, "default": 5000.0, "min": 100.0, "max": 50000.0, "unit": "t", "label": "Storage Capacity"},
            "initial_level_pct": {"type": float, "default": 65.0, "min": 0.0, "max": 100.0, "unit": "%", "label": "Initial Level"},
        }

    def initialize(self):
        cap = float(self.parameters.get("capacity_tons", 5000.0))
        lvl = float(self.parameters.get("initial_level_pct", 65.0))
        self.state = {
            "level_pct": lvl,
            "stored_tons": round(cap * lvl / 100.0, 1),
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_stream = inlet_streams.get("in_solid")
        out_stream = outlet_streams.get("out_solid")

        flow = in_stream.mass_flow_tph if in_stream else 0.0
        temp = in_stream.temperature_c if in_stream else 25.0
        comp = in_stream.composition if in_stream else {}

        if out_stream:
            out_stream.update_state(
                mass_flow_tph=flow,
                temperature_c=temp,
                pressure_mbar=0.0,
                composition=comp,
            )
        return outlet_streams
