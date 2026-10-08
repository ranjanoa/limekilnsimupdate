"""
CycloneStage: Preheater cyclone stage modeling counter-current gas-solid heat exchange,
mechanical separation efficiency, draft pressure drop, and dust carryover.
"""

from typing import Dict, List, Any
import copy

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class CycloneStage(BlockBase):
    """
    Suspension Preheater Cyclone Stage.
    Performs counter-current convective and radiative thermal exchange between
    hot exhaust gas and colder raw meal particles, followed by centrifugal gas-solid separation.
    """
    block_type = "CycloneStage"
    category = "Separation"
    icon = "cyclone"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_gas", PortDirection.IN, StreamPhase.GAS, "Rising hot flue gas from stage below", required=True),
            Port("in_meal", PortDirection.IN, StreamPhase.SOLID, "Descending meal from stage above or feeder", required=True),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Cooled gas exiting to upper stage or ID fan", required=True),
            Port("out_meal", PortDirection.OUT, StreamPhase.SOLID, "Preheated meal discharging from dipleg", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "stage_number": {"type": int, "default": 1, "min": 1, "max": 6, "unit": "#", "label": "Preheater Stage (1=Top, 5=Bottom)"},
            "separation_efficiency": {"type": float, "default": 0.95, "min": 0.70, "max": 0.999, "unit": "-", "label": "Separation Efficiency η"},
            "thermal_effectiveness": {"type": float, "default": 0.82, "min": 0.50, "max": 0.95, "unit": "-", "label": "Heat Exchanger Effectiveness ε"},
            "dp_mbar": {"type": float, "default": 5.5, "min": 1.0, "max": 15.0, "unit": "mbar", "label": "Stage Draft Drop ΔP"},
            "heat_loss_pct": {"type": float, "default": 1.5, "min": 0.0, "max": 10.0, "unit": "%", "label": "Vessel Radiation Loss"},
        }

    def initialize(self):
        stage = int(self.parameters.get("stage_number", 1))
        # Default nominal temperatures based on stage (Kiln 3 calibration)
        nominal_temps = {
            1: {"gas_out": 330.0, "meal_out": 310.0},
            2: {"gas_out": 520.0, "meal_out": 490.0},
            3: {"gas_out": 680.0, "meal_out": 640.0},
            4: {"gas_out": 810.0, "meal_out": 760.0},
            5: {"gas_out": 880.0, "meal_out": 860.0},
        }
        t_ref = nominal_temps.get(stage, {"gas_out": 500.0, "meal_out": 480.0})

        self.state = {
            "gas_temp_c": t_ref["gas_out"],
            "meal_temp_c": t_ref["meal_out"],
            "pressure_drop_mbar": float(self.parameters.get("dp_mbar", 5.5)),
            "heat_transferred_gjh": 0.0,
            "heat_loss_gjh": 0.0,
            "dust_carryover_tph": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_gas = inlet_streams.get("in_gas")
        in_meal = inlet_streams.get("in_meal")
        out_gas = outlet_streams.get("out_gas")
        out_meal = outlet_streams.get("out_meal")

        m_gas = in_gas.mass_flow_tph if in_gas else 0.0
        m_meal = in_meal.mass_flow_tph if in_meal else 0.0

        t_gas_in = in_gas.temperature_c if in_gas else 800.0
        t_meal_in = in_meal.temperature_c if in_meal else 60.0
        p_gas_in = in_gas.pressure_mbar if in_gas else 0.0

        eta = float(self.parameters.get("separation_efficiency", 0.95))
        eps = float(self.parameters.get("thermal_effectiveness", 0.82))
        dp = float(self.parameters.get("dp_mbar", 5.5))
        loss_pct = float(self.parameters.get("heat_loss_pct", 1.5)) / 100.0

        if m_gas > 0.0 and m_meal > 0.0:
            cp_gas = in_gas.get_heat_capacity_kcal_kg_c() * 4.184  # kJ/(kg*C)
            cp_meal = in_meal.get_heat_capacity_kcal_kg_c() * 4.184

            c_gas = m_gas * cp_gas      # GJ / (h * C) * 1000
            c_meal = m_meal * cp_meal
            c_min = min(c_gas, c_meal)

            delta_t_max = max(0.0, t_gas_in - t_meal_in)
            q_transfer = eps * c_min * delta_t_max  # scaled energy transfer

            # Ambient heat loss from cyclone steel casing
            q_loss = loss_pct * c_gas * max(0.0, t_gas_in - 25.0)

            t_gas_out = max(t_meal_in + 10.0, t_gas_in - (q_transfer + q_loss) / max(1.0, c_gas))
            t_meal_out = min(t_gas_in - 10.0, t_meal_in + q_transfer / max(1.0, c_meal))

            q_transfer_gjh = (q_transfer / 1000.0)
            q_loss_gjh = (q_loss / 1000.0)
        else:
            t_gas_out = t_gas_in
            t_meal_out = t_meal_in
            q_transfer_gjh = 0.0
            q_loss_gjh = 0.0

        # Gas-Solid Separation
        m_meal_collected = m_meal * eta
        dust_carryover = m_meal * (1.0 - eta)
        m_gas_out = m_gas + dust_carryover

        p_gas_out = p_gas_in - dp

        # Update block state
        self.state["gas_temp_c"] = round(t_gas_out, 1)
        self.state["meal_temp_c"] = round(t_meal_out, 1)
        self.state["heat_transferred_gjh"] = round(q_transfer_gjh, 2)
        self.state["heat_loss_gjh"] = round(q_loss_gjh, 2)
        self.state["dust_carryover_tph"] = round(dust_carryover, 2)
        self.state["pressure_drop_mbar"] = dp

        # Update output streams
        if out_gas:
            comp_gas = copy.deepcopy(in_gas.composition) if in_gas else {}
            out_gas.update_state(
                mass_flow_tph=m_gas_out,
                temperature_c=t_gas_out,
                pressure_mbar=p_gas_out,
                composition=comp_gas,
            )

        if out_meal:
            comp_meal = copy.deepcopy(in_meal.composition) if in_meal else {}
            out_meal.update_state(
                mass_flow_tph=m_meal_collected,
                temperature_c=t_meal_out,
                pressure_mbar=p_gas_in,
                composition=comp_meal,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic ODE step integrating cyclone gas-solid thermal capacitance."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        t_gas_tgt = self.state["gas_temp_c"]
        t_meal_tgt = self.state["meal_temp_c"]

        curr_gas = self.state.get("dynamic_gas_temp_c", t_gas_tgt)
        curr_meal = self.state.get("dynamic_meal_temp_c", t_meal_tgt)

        tau_cyc = 8.0  # seconds

        new_gas = curr_gas + (t_gas_tgt - curr_gas) * (dt / max(0.1, tau_cyc))
        new_meal = curr_meal + (t_meal_tgt - curr_meal) * (dt / max(0.1, tau_cyc))

        self.state["dynamic_gas_temp_c"] = round(new_gas, 1)
        self.state["dynamic_meal_temp_c"] = round(new_meal, 1)
        self.state["gas_temp_c"] = round(new_gas, 1)
        self.state["meal_temp_c"] = round(new_meal, 1)

        out_gas = outlet_streams.get("out_gas")
        if out_gas:
            out_gas.temperature_c = round(new_gas, 1)
            out_gas.compute_enthalpy()
        out_meal = outlet_streams.get("out_meal")
        if out_meal:
            out_meal.temperature_c = round(new_meal, 1)
            out_meal.compute_enthalpy()

