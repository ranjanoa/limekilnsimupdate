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
        speed = max(0.1, float(self.parameters.get("speed_rpm", 3.79)))
        l = float(self.parameters.get("length_m", 72.0))
        d = float(self.parameters.get("diameter_m", 4.6))
        s = float(self.parameters.get("slope_pct", 3.5)) / 100.0
        theta = 35.0
        residence_min = (1.77 * l * math.sqrt(theta)) / (s * d * speed * 60.0)

        is_lime = bz_temp < 1350.0 or speed < 2.5
        clk_nom = 58.5 if is_lime else 175.0
        holdup_nom = clk_nom * (residence_min / 60.0)
        v_shell = math.pi * ((d / 2.0) ** 2) * l
        v_bed = holdup_nom / 1.35
        filling_pct = (v_bed / max(1.0, v_shell)) * 100.0
        phi_ref = 9.5
        filling_ratio = max(0.2, min(3.0, filling_pct / phi_ref))
        n_ref = 2.2 if is_lime else 3.79
        speed_ratio = speed / n_ref

        t_torque_nom = 145.0 if is_lime else 182.0
        i_nom = 185.0 if is_lime else 254.0
        torque_kwn = t_torque_nom * (0.30 + 0.70 * filling_ratio)
        omega = 2.0 * math.pi * speed / 60.0
        power_kw = torque_kwn * omega
        motor_current_a = i_nom * (0.20 + 0.45 * speed_ratio + 0.35 * filling_ratio)

        self.state = {
            "burning_zone_temp_c": bz_temp,
            "kiln_inlet_gas_temp_c": 1050.0,
            "bed_residence_time_min": round(residence_min, 1),
            "bed_filling_degree_pct": round(filling_pct, 2),
            "bed_holdup_tons": round(holdup_nom, 1),
            "kiln_drive_torque_kwn": round(torque_kwn, 1),
            "kiln_drive_current_a": round(motor_current_a, 1),
            "kiln_drive_power_kw": round(power_kw, 1),
            "clinker_rate_tph": round(clk_nom, 2),
            "free_lime_pct": 1.15,
            "c3s_pct": 62.4,
            "residual_caco3_pct": 1.1,
            "active_cao_pct": 92.5,
            "reactivity_t60_s": 38.0,
            "kiln_inlet_o2_pct": 2.32,
            "kiln_inlet_co_pct": 0.04,
            "kiln_inlet_nox_ppm": 850.0,
            "heat_loss_gjh": round(float(self.parameters.get("shell_heat_loss_mw", 14.8)) * 3.6, 2),
            # Internal dynamic states (exact unrounded floats)
            "dynamic_bz_temp_c": bz_temp,
            "dynamic_clinker_tph": clk_nom,
            "dynamic_holdup_tons": holdup_nom,
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

        # 1. Geometry & Saeman Residence Time
        l = float(self.parameters.get("length_m", 72.0))
        d = float(self.parameters.get("diameter_m", 4.6))
        s = float(self.parameters.get("slope_pct", 3.5)) / 100.0
        n = max(0.1, float(self.parameters.get("speed_rpm", 3.79)))
        theta = 35.0  # angle of repose
        residence_min = (1.77 * l * math.sqrt(theta)) / (s * d * n * 60.0)

        # Baseline reference sizing based on lime kiln vs cement kiln
        in_caco3_pct = float(in_meal.composition.get("CaCO3_pct", 6.0)) if in_meal else 6.0
        is_lime_kiln = in_caco3_pct > 70.0

        n_ref = 2.2 if is_lime_kiln else 3.79
        m_meal_ref = 100.0 if is_lime_kiln else 181.2
        t_bz_base = float(self.parameters.get("target_burning_zone_c", 1280.0 if is_lime_kiln else 1435.0))
        i_nom = 185.0 if is_lime_kiln else 254.0
        t_torque_nom = 145.0 if is_lime_kiln else 182.0

        # 2. Burner Combustion & Mass Balance
        lhv = in_fuel.composition.get("lhv_mj_kg", 31.4) if in_fuel else 31.4
        caco3_resid = m_meal * (in_caco3_pct / 100.0)
        m_co2_resid = caco3_resid * 0.4397

        ash_pct = in_fuel.composition.get("ash_pct", 1.0) / 100.0 if in_fuel else 0.01
        m_ash_in = m_fuel * ash_pct
        m_clinker = max(0.0, m_meal - m_co2_resid + m_ash_in)
        m_gas_out = m_sec_air + m_pri_air + (m_fuel - m_ash_in) + m_co2_resid

        # 3. Bed Material Holdup & Volumetric Filling Degree
        # Internal shell volume: V = pi * (D/2)^2 * L
        v_shell = math.pi * ((d / 2.0) ** 2) * l
        m_holdup = max(1.0, m_clinker * (residence_min / 60.0))
        rho_bulk = 1.35  # bulk density of mineral bed (t/m3)
        v_bed = m_holdup / rho_bulk
        filling_pct = (v_bed / max(1.0, v_shell)) * 100.0
        phi_ref = 9.5  # nominal filling degree (%)
        filling_ratio = max(0.2, min(3.0, filling_pct / phi_ref))
        speed_ratio = n / n_ref

        # 4. Kiln Drive Torque, Mechanical Power, and Motor Current
        # Mechanical torque: 30% mechanical/roller friction + 70% bed lifting torque
        torque_kwn = t_torque_nom * (0.30 + 0.70 * filling_ratio)
        # Mechanical power: P = T * omega = T * (2*pi*N / 60)
        omega = 2.0 * math.pi * n / 60.0
        power_kw = torque_kwn * omega
        # Drive Motor Current: increases with rotational speed (higher shaft power) and bed loading (torque)
        motor_current_a = i_nom * (0.20 + 0.45 * speed_ratio + 0.35 * filling_ratio)

        # 5. Coupled Thermal Balance with Speed Transit Effect
        m_fuel_ref = 5.2 if is_lime_kiln else 7.20
        lhv_ref = 46.5 if is_lime_kiln else 31.4
        t_sec_ref = 650.0 if is_lime_kiln else 1020.0
        m_sec_ref = 90.0 if is_lime_kiln else 84.3

        dq_flame = (m_fuel * lhv - m_fuel_ref * lhv_ref) * 0.98
        dq_meal = (m_meal - m_meal_ref) * 0.55
        t_sec = in_sec_air.temperature_c if in_sec_air else t_sec_ref
        dq_sec = (m_sec_air * max(0.0, t_sec - 25.0) - m_sec_ref * (t_sec_ref - 25.0)) * 0.26 * 4.184 / 1000.0

        dq_net = dq_flame - dq_meal + dq_sec
        c_bz = 0.28
        # Speed effect on burning zone: higher speed pushes colder material faster, depressing temperature
        speed_cooling_bz = -35.0 * (speed_ratio - 1.0)
        t_bz_target = t_bz_base + (dq_net / c_bz) + speed_cooling_bz
        t_bz_target = max(1050.0, min(1600.0, t_bz_target))

        # Combustion stoichiometry & Gas Analysis
        m_air_in = m_sec_air + m_pri_air
        m_air_stoich = m_fuel * (14.2 if is_lime_kiln else 10.5)
        lambda_kiln = m_air_in / max(0.1, m_air_stoich) if m_fuel > 0.1 else 1.19
        o2_target = max(0.5, min(8.0, 2.32 + (lambda_kiln - 1.19) * 8.5))
        co_target = max(0.01, min(3.50, 0.04 + max(0.0, 1.8 - o2_target) * 0.45))
        nox_target = round(850.0 * math.exp(0.0035 * (t_bz_target - 1435.0)), 0)

        # Flue gas exit temperature at kiln inlet
        speed_gas_effect = 18.0 * (speed_ratio - 1.0)
        t_kiln_gas = round(1050.8 + 0.35 * (t_bz_target - 1435.0) - 0.20 * (m_meal - m_meal_ref) + speed_gas_effect, 1)
        t_kiln_gas = max(750.0, min(1200.0, t_kiln_gas))
        t_clinker = t_bz_target - 15.0
        shell_loss_gjh = float(self.parameters.get("shell_heat_loss_mw", 14.8)) * 3.6

        # 6. Quality & Decarbonation Kinetics Coupled to Residence Time & Temperature
        t_res_nom = 32.0 if is_lime_kiln else 20.6
        t_res_ratio = max(0.2, residence_min / t_res_nom)
        f_cao = 1.30 * math.exp(-0.015 * (t_bz_target - 1435.0)) * math.pow(max(50.0, m_meal) / m_meal_ref, 0.5) / math.pow(t_res_ratio, 0.4)
        f_cao = round(max(0.1, min(6.0, f_cao)), 2)
        c3s = round(max(30.0, min(75.0, 60.1 + 0.04 * (t_bz_target - 1435.0) - 1.2 * (f_cao - 1.30) + 2.0 * (t_res_ratio - 1.0))), 1)

        scale_lime = (m_meal / max(1.0, m_clinker))
        resid_caco3 = 1.10 * math.exp(-0.007 * (t_bz_target - 1280.0)) / math.pow(t_res_ratio, 0.9)
        resid_caco3 = round(max(0.3, min(18.0, resid_caco3)), 2)

        in_sio2 = float(in_meal.composition.get("SiO2_pct", 2.2)) if in_meal else 2.2
        in_mgo = float(in_meal.composition.get("MgCO3_pct", 1.8)) * 0.478 if in_meal else 0.9
        sio2_out = round(in_sio2 * scale_lime, 1)
        mgo_out = round(in_mgo * scale_lime, 1)
        active_cao = round(max(75.0, min(97.0, 100.0 - resid_caco3 - sio2_out - mgo_out - 1.2)), 1)

        reactivity_s = 35.0 + max(0.0, t_bz_target - 1260.0) * 0.25 + max(0.0, residence_min - 28.5) * 1.5
        if resid_caco3 > 3.0:
            reactivity_s += (resid_caco3 - 3.0) * 4.0
        reactivity_s = round(max(20.0, min(240.0, reactivity_s)), 0)

        # Update block state
        self.state["burning_zone_temp_c"] = round(t_bz_target, 1)
        self.state["kiln_inlet_gas_temp_c"] = round(t_kiln_gas, 1)
        self.state["bed_residence_time_min"] = round(residence_min, 1)
        self.state["bed_filling_degree_pct"] = round(filling_pct, 2)
        self.state["bed_holdup_tons"] = round(m_holdup, 1)
        self.state["kiln_drive_torque_kwn"] = round(torque_kwn, 1)
        self.state["kiln_drive_power_kw"] = round(power_kw, 1)
        self.state["kiln_drive_current_a"] = round(motor_current_a, 1)
        self.state["clinker_rate_tph"] = round(m_clinker, 2)
        self.state["free_lime_pct"] = round(f_cao, 2)
        self.state["c3s_pct"] = round(c3s, 1)
        self.state["residual_caco3_pct"] = round(resid_caco3, 2)
        self.state["active_cao_pct"] = round(active_cao, 1)
        self.state["reactivity_t60_s"] = round(reactivity_s, 0)
        self.state["kiln_inlet_o2_pct"] = round(o2_target, 2)
        self.state["kiln_inlet_co_pct"] = round(co_target, 3)
        self.state["kiln_inlet_nox_ppm"] = round(nox_target, 0)
        self.state["heat_loss_gjh"] = round(shell_loss_gjh, 2)

        # Update outlet streams
        out_clinker = outlet_streams.get("out_clinker")
        if out_clinker:
            if is_lime_kiln:
                clinker_comp = {
                    "Active_CaO_pct": active_cao,
                    "Residual_CaCO3_pct": resid_caco3,
                    "SiO2_pct": sio2_out,
                    "MgO_pct": mgo_out,
                    "Reactivity_s": reactivity_s,
                }
            else:
                clinker_comp = {
                    "C3S_pct": c3s,
                    "C2S_pct": round(76.0 - c3s, 1),
                    "C3A_pct": 7.8,
                    "C4AF_pct": 10.2,
                    "Free_CaO_pct": f_cao,
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
                    "O2_pct": round(o2_target, 2),
                    "CO_pct": round(co_target, 3),
                    "CO2_pct": 22.5,
                    "N2_pct": round(77.5 - o2_target - co_target, 1),
                    "NOx_ppm": round(nox_target, 0),
                    "H2O_pct": 4.3,
                },
            )

        # Align dynamic states if uninitialized
        if "dynamic_clinker_tph" not in self.state or self.state.get("dynamic_clinker_tph") is None:
            self.state["dynamic_clinker_tph"] = m_clinker
        if "dynamic_holdup_tons" not in self.state or self.state.get("dynamic_holdup_tons") is None:
            self.state["dynamic_holdup_tons"] = m_holdup
        if "dynamic_bz_temp_c" not in self.state or self.state.get("dynamic_bz_temp_c") is None:
            self.state["dynamic_bz_temp_c"] = t_bz_target

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic ODE step integrating kiln thermal inertia, dynamic bed holdup, and transport surge."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        t_bz_target = self.state["burning_zone_temp_c"]
        m_clinker_target = self.state["clinker_rate_tph"]
        m_holdup_target = self.state["bed_holdup_tons"]
        residence_min = max(0.5, self.state["bed_residence_time_min"])
        residence_hr = residence_min / 60.0
        n = max(0.1, float(self.parameters.get("speed_rpm", 3.79)))
        in_caco3_pct = float(inlet_streams.get("in_meal_calcined").composition.get("CaCO3_pct", 6.0)) if inlet_streams.get("in_meal_calcined") else 6.0
        n_ref = 2.2 if in_caco3_pct > 70.0 else 3.79

        current_tbz = float(self.state.get("dynamic_bz_temp_c", t_bz_target))
        current_clk = float(self.state.get("dynamic_clinker_tph", m_clinker_target))
        current_holdup = float(self.state.get("dynamic_holdup_tons", m_holdup_target))

        # 1. Thermal inertia: refractory & bed heat capacity (tau ~ 60s)
        tau_bz = 60.0  # seconds
        new_tbz = current_tbz + (t_bz_target - current_tbz) * (dt / max(0.1, tau_bz))

        # 2. Material bed transport and holdup dynamics:
        # Transit time constant scales inversely with rotational speed
        tau_transit = max(10.0, 30.0 * (n_ref / n))

        # Instantaneous discharge demand from tumbling bed:
        # Material at discharge end is driven by current bed inventory divided by residence time
        dynamic_discharge_demand = current_holdup / residence_hr

        # Smooth discharge flow filter
        new_clk = current_clk + (dynamic_discharge_demand - current_clk) * (dt / max(0.5, tau_transit * 0.25))

        # Exact mass conservation ODE for bed holdup:
        # Inflow is target clinker formation from feed; outflow is actual clinker discharged
        d_holdup = (m_clinker_target - new_clk) * (dt / 3600.0)
        new_holdup = max(1.0, current_holdup + d_holdup)

        # Recompute dynamic filling degree and motor metrics based on live dynamic holdup
        l = float(self.parameters.get("length_m", 72.0))
        d = float(self.parameters.get("diameter_m", 4.6))
        v_shell = math.pi * ((d / 2.0) ** 2) * l
        v_bed = new_holdup / 1.35
        dyn_filling_pct = (v_bed / max(1.0, v_shell)) * 100.0
        dyn_filling_ratio = max(0.2, min(3.0, dyn_filling_pct / 9.5))

        i_nom = 185.0 if in_caco3_pct > 70.0 else 254.0
        t_nom = 145.0 if in_caco3_pct > 70.0 else 182.0
        dyn_torque = t_nom * (0.30 + 0.70 * dyn_filling_ratio)
        dyn_power = dyn_torque * (2.0 * math.pi * n / 60.0)
        dyn_current = i_nom * (0.20 + 0.45 * (n / n_ref) + 0.35 * dyn_filling_ratio)

        # Store exact unrounded floats for dynamic ODE integrator states
        self.state["dynamic_bz_temp_c"] = new_tbz
        self.state["dynamic_clinker_tph"] = new_clk
        self.state["dynamic_holdup_tons"] = new_holdup

        # Store rounded states for telemetry and displays
        self.state["burning_zone_temp_c"] = round(new_tbz, 1)
        self.state["clinker_rate_tph"] = round(new_clk, 2)
        self.state["bed_holdup_tons"] = round(new_holdup, 1)
        self.state["bed_filling_degree_pct"] = round(dyn_filling_pct, 2)
        self.state["kiln_drive_torque_kwn"] = round(dyn_torque, 1)
        self.state["kiln_drive_power_kw"] = round(dyn_power, 1)
        self.state["kiln_drive_current_a"] = round(dyn_current, 1)

        # Dynamic kinetics based on live dynamic BZ temperature
        t_res_nom = 32.0 if in_caco3_pct > 70.0 else 20.6
        t_res_ratio = max(0.2, residence_min / t_res_nom)
        if in_caco3_pct > 70.0:
            resid_caco3 = 1.10 * math.exp(-0.007 * (new_tbz - 1280.0)) / math.pow(t_res_ratio, 0.9)
            resid_caco3 = round(max(0.3, min(18.0, resid_caco3)), 2)
            self.state["residual_caco3_pct"] = resid_caco3
            self.state["active_cao_pct"] = round(max(75.0, min(97.0, 98.0 - resid_caco3 - 4.5)), 1)
        else:
            f_cao = 1.30 * math.exp(-0.015 * (new_tbz - 1435.0)) / math.pow(t_res_ratio, 0.4)
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

