"""
RotaryKiln: Pyroprocessing rotary kiln unit operation modeling Saeman bed transport,
main burner radiative flame heat transfer, clinker sintering, free lime kinetics, and shell losses.
"""

from typing import Dict, List, Any
import math

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class RotaryKiln(BlockBase):
    """
    Industrial Rotary Kiln Unit Operation.
    Transports mineral bed counter-currently against hot combustion gases,
    completes residual calcination, and sinters alite (C3S) clinker nodules at 1450°C.
    """
    block_type = "RotaryKiln"
    category = "Pyroprocess"
    icon = "kiln"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_meal_calcined", PortDirection.IN, StreamPhase.SOLID, "Calcined hot meal from calciner/bottom cyclone", required=True),
            Port("in_flame_fuel", PortDirection.IN, StreamPhase.FUEL, "Kiln main burner fuel (petcoke / alternative fuels)", required=True),
            Port("in_secondary_air", PortDirection.IN, StreamPhase.AIR, "Preheated secondary air from cooler hood", required=True),
            Port("in_primary_air", PortDirection.IN, StreamPhase.AIR, "Burner primary momentum air", required=False),
            Port("out_clinker", PortDirection.OUT, StreamPhase.SOLID, "Sintered hot clinker discharging into grate cooler", required=True),
            Port("out_kiln_gas", PortDirection.OUT, StreamPhase.GAS, "Kiln exhaust flue gas discharging into calciner riser", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "length_m": {"type": float, "default": 72.0, "min": 20.0, "max": 150.0, "unit": "m", "label": "Kiln Shell Length"},
            "diameter_m": {"type": float, "default": 4.6, "min": 2.0, "max": 7.0, "unit": "m", "label": "Internal Diameter"},
            "slope_pct": {"type": float, "default": 3.5, "min": 1.0, "max": 6.0, "unit": "%", "label": "Axis Slope"},
            "speed_rpm": {"type": float, "default": 3.79, "min": 0.5, "max": 5.5, "unit": "rpm", "label": "Rotation Speed"},
            "target_burning_zone_c": {"type": float, "default": 1435.0, "min": 1300.0, "max": 1550.0, "unit": "°C", "label": "Burning Zone SP"},
            "shell_heat_loss_mw": {"type": float, "default": 14.8, "min": 5.0, "max": 30.0, "unit": "MW", "label": "Shell Thermal Losses"},
        }

    def initialize(self):
        bz_temp = float(self.parameters.get("target_burning_zone_c", 1435.0))
        self.state = {
            "burning_zone_temp_c": bz_temp,
            "kiln_inlet_gas_temp_c": 1050.0,
            "kiln_drive_torque_kwn": 182.0,
            "bed_residence_time_min": 28.5,
            "free_lime_pct": 1.15,
            "c3s_pct": 62.4,
            "clinker_rate_tph": 175.0,
            "heat_loss_gjh": round(float(self.parameters.get("shell_heat_loss_mw", 14.8)) * 3.6, 2),
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_meal = inlet_streams.get("in_meal_calcined")
        in_fuel = inlet_streams.get("in_flame_fuel")
        in_sec_air = inlet_streams.get("in_secondary_air")
        in_pri_air = inlet_streams.get("in_primary_air")

        m_meal = in_meal.mass_flow_tph if in_meal else 0.0
        m_fuel = in_fuel.mass_flow_tph if in_fuel else 0.0
        m_sec_air = in_sec_air.mass_flow_tph if in_sec_air else 0.0
        m_pri_air = in_pri_air.mass_flow_tph if in_pri_air else 0.0

        # Saeman residence time calculation
        l = float(self.parameters.get("length_m", 72.0))
        d = float(self.parameters.get("diameter_m", 4.6))
        s = float(self.parameters.get("slope_pct", 3.5)) / 100.0
        n = max(0.1, float(self.parameters.get("speed_rpm", 3.79)))
        theta = 35.0  # angle of repose
        residence_min = (1.77 * l * math.sqrt(theta)) / (s * d * n * 60.0)

        # Main burner heat input
        lhv = in_fuel.composition.get("lhv_mj_kg", 31.4) if in_fuel else 31.4
        q_burner_gjh = m_fuel * lhv

        # Residual decarbonation based on incoming CaCO3 (raw limestone or precalcined meal)
        in_caco3_pct = float(in_meal.composition.get("CaCO3_pct", 6.0)) if in_meal else 6.0
        caco3_resid = m_meal * (in_caco3_pct / 100.0)
        m_co2_resid = caco3_resid * 0.4397
        q_calc_resid = caco3_resid * 1.782

        # Sintering clinker formation: meal mass minus residual CO2 plus fuel ash incorporation
        ash_pct = in_fuel.composition.get("ash_pct", 1.0) / 100.0 if in_fuel else 0.01
        m_ash_in = m_fuel * ash_pct
        m_clinker = max(0.0, m_meal - m_co2_resid + m_ash_in)

        # Flue gas from main burner combustion: secondary air + primary air + fuel mass (minus ash) + residual CO2
        m_gas_out = m_sec_air + m_pri_air + (m_fuel - m_ash_in) + m_co2_resid

        # Coupled first-principles burning zone thermal balance
        # Baseline reference: fuel = 7.20 t/h (LHV 31.4), meal = 181.2 t/h, sec_air = 84.3 t/h @ 1020C
        m_fuel_ref = 7.20
        lhv_ref = 31.4
        m_meal_ref = 181.2
        t_sec_ref = 1020.0
        m_sec_ref = 84.3

        dq_flame = (m_fuel * lhv - m_fuel_ref * lhv_ref) * 0.98  # GJ/h flame thermal input delta
        dq_meal = (m_meal - m_meal_ref) * 0.55  # Bed sensible load to heat meal from 1000C to 1435C
        t_sec = in_sec_air.temperature_c if in_sec_air else t_sec_ref
        dq_sec = (m_sec_air * max(0.0, t_sec - 25.0) - m_sec_ref * (t_sec_ref - 25.0)) * 0.26 * 4.184 / 1000.0

        dq_net = dq_flame - dq_meal + dq_sec
        c_bz = 0.28  # Effective burning zone thermal capacity rate GJ/(h*C)
        t_bz_target = 1435.0 + (dq_net / c_bz)
        t_bz_target = max(1150.0, min(1600.0, t_bz_target))

        # Clinker free lime kinetics: fCaO decreases exponentially as BZ temperature increases
        f_cao = 1.30 * math.exp(-0.015 * (t_bz_target - 1435.0)) * math.pow(max(50.0, m_meal) / m_meal_ref, 0.5)
        f_cao = round(max(0.1, min(6.0, f_cao)), 2)
        c3s = round(max(30.0, min(75.0, 60.1 + 0.04 * (t_bz_target - 1435.0) - 1.2 * (f_cao - 1.30))), 1)

        # Flue gas exit temperature at kiln inlet (~1050°C), coupled to burning zone
        t_kiln_gas = round(1050.8 + 0.35 * (t_bz_target - 1435.0) - 0.20 * (m_meal - m_meal_ref), 1)
        t_kiln_gas = max(850.0, min(1200.0, t_kiln_gas))
        t_clinker = t_bz_target - 15.0
        shell_loss_gjh = float(self.parameters.get("shell_heat_loss_mw", 14.8)) * 3.6

        # Update block state
        self.state["burning_zone_temp_c"] = round(t_bz_target, 1)
        self.state["kiln_inlet_gas_temp_c"] = round(t_kiln_gas, 1)
        self.state["bed_residence_time_min"] = round(residence_min, 1)
        self.state["clinker_rate_tph"] = round(m_clinker, 2)
        self.state["free_lime_pct"] = round(f_cao, 2)
        self.state["c3s_pct"] = round(c3s, 1)
        self.state["heat_loss_gjh"] = round(shell_loss_gjh, 2)

        # Update outlet streams
        out_clinker = outlet_streams.get("out_clinker")
        if out_clinker:
            is_lime_kiln = in_caco3_pct > 70.0
            if is_lime_kiln:
                scale_lime = (m_meal / max(1.0, m_clinker))
                quicklime_cao = min(98.0, max(85.0, (in_caco3_pct * 56.08 / 100.09) * scale_lime))
                clinker_comp = {
                    "Active_CaO_pct": round(quicklime_cao, 1),
                    "Residual_CaCO3_pct": round(max(0.5, 100.0 - quicklime_cao - 3.5), 1),
                    "SiO2_pct": round(in_meal.composition.get("SiO2_pct", 2.2) * scale_lime, 1) if in_meal else 2.2,
                    "MgO_pct": round(in_meal.composition.get("MgCO3_pct", 1.8) * 0.478 * scale_lime, 1) if in_meal else 1.0,
                    "Reactivity_s": round(max(25.0, 180.0 - (t_bz_target - 1200.0) * 0.4), 0),
                }
            else:
                clinker_comp = {
                    "C3S_pct": round(c3s, 1),
                    "C2S_pct": round(76.0 - c3s, 1),
                    "C3A_pct": 7.8,
                    "C4AF_pct": 10.2,
                    "Free_CaO_pct": round(f_cao, 2),
                    "MgO_pct": 1.4,
                }
            out_clinker.update_state(
                mass_flow_tph=m_clinker,
                temperature_c=t_clinker,
                pressure_mbar=0.0,
                composition=clinker_comp,
            )

        out_gas = outlet_streams.get("out_kiln_gas")
        if out_gas:
            out_gas.update_state(
                mass_flow_tph=m_gas_out,
                temperature_c=t_kiln_gas,
                pressure_mbar=-1.8,
                composition={
                    "O2_pct": 2.2,
                    "CO2_pct": 22.5,
                    "N2_pct": 71.0,
                    "H2O_pct": 4.3,
                },
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic ODE step integrating kiln thermal inertia and bed residence transport."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        t_bz_target = self.state["burning_zone_temp_c"]
        m_clinker_target = self.state["clinker_rate_tph"]

        current_tbz = self.state.get("dynamic_bz_temp_c", t_bz_target)
        current_clk = self.state.get("dynamic_clinker_tph", m_clinker_target)

        # Thermal inertia of refractory & clinkering bed: tau ~ 60s
        tau_bz = 60.0  # seconds
        # Bed transport transit delay: tau ~ 120s
        tau_bed = 120.0  # seconds

        new_tbz = current_tbz + (t_bz_target - current_tbz) * (dt / max(0.1, tau_bz))
        new_clk = current_clk + (m_clinker_target - current_clk) * (dt / max(0.1, tau_bed))

        self.state["dynamic_bz_temp_c"] = round(new_tbz, 1)
        self.state["dynamic_clinker_tph"] = round(new_clk, 2)
        self.state["burning_zone_temp_c"] = round(new_tbz, 1)
        self.state["clinker_rate_tph"] = round(new_clk, 2)

        # Dynamic kinetics based on live dynamic BZ temperature
        f_cao = 1.30 * math.exp(-0.015 * (new_tbz - 1435.0))
        self.state["free_lime_pct"] = round(max(0.1, min(6.0, f_cao)), 2)

        out_clinker = outlet_streams.get("out_clinker")
        if out_clinker:
            out_clinker.temperature_c = round(new_tbz - 15.0, 1)
            out_clinker.mass_flow_tph = round(new_clk, 2)
            out_clinker.compute_enthalpy()
        out_gas = outlet_streams.get("out_kiln_gas")
        if out_gas:
            t_kg = round(1050.8 + 0.35 * (new_tbz - 1435.0), 1)
            out_gas.temperature_c = t_kg
            out_gas.compute_enthalpy()

