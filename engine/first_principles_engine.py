"""
CONFIGURABLE FIRST-PRINCIPLES CEMENT PYROPROCESS ENGINE
Coupled Dynamic ODE Simulation Engine with Optimization Interface
Reads parameters from config/plant_config.json
"""

import json
import logging
import math
import os
import time

logger = logging.getLogger("FirstPrinciplesEngine")

class FirstPrinciplesEngine:
    def __init__(self, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "plant_config.json")
        self.config_path = config_path
        self.load_configuration()
        self.reset_to_nominal()

    def load_configuration(self):
        """Loads or reloads configuration parameters from JSON file."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        # Cache config sections
        self.cfg_sim = self.cfg.get("simulation", {})
        self.cfg_raw = self.cfg.get("raw_material", {})
        self.cfg_fuels = self.cfg.get("fuels", {})
        self.cfg_dims = self.cfg.get("equipment_dimensions", {})
        self.cfg_kin = self.cfg.get("reaction_kinetics", {})
        self.cfg_ctrl = self.cfg.get("controllers", {})
        self.cfg_opc = self.cfg.get("opc_ua", {})
        self.tag_dictionary = self.cfg.get("tag_dictionary", [])
        self.tag_dict_map = {t["tag_id"]: t for t in self.tag_dictionary}
        if not hasattr(self, "local_setpoints"):
            self.local_setpoints = {}
        if not hasattr(self, "custom_tag_values"):
            self.custom_tag_values = {}

        self.nominal_feed = self.cfg_sim.get("nominal_feed_rate_tph", 280.0)
        self.nominal_clinker = self.cfg_sim.get("nominal_clinker_rate_tph", 175.0)
        self.clinker_factor = self.nominal_feed / self.nominal_clinker

    def reset_to_nominal(self):
        """Resets all dynamic state variables to nominal operating point."""
        # Feed & Production
        self.raw_meal_feed = self.nominal_feed
        self.clinker_production = self.nominal_clinker
        
        # Rotary Kiln States
        kiln_dims = self.cfg_dims.get("rotary_kiln", {})
        self.kiln_speed = kiln_dims.get("nominal_speed_rpm", 3.79)
        self.kiln_amps = kiln_dims.get("nominal_drive_amps", 254.0)
        self.filling_degree = kiln_dims.get("nominal_filling_degree_pct", 10.96)
        self.sintering_temp = self.cfg_kin.get("clinkerization", {}).get("nominal_sintering_temp_c", 1450.0)
        self.burning_zone_t1 = self.sintering_temp - 143.0
        self.burning_zone_t2 = self.sintering_temp - 133.0
        self.shell_temp = 305.0
        self.free_lime = self.cfg_kin.get("clinkerization", {}).get("nominal_free_lime_pct", 1.30)
        self.kiln_inlet_temp = 1050.0
        self.kiln_inlet_press = -1.3
        self.kiln_inlet_o2 = 2.32
        self.kiln_inlet_nox = 857.0
        self.kiln_inlet_co = 0.004
        self.kiln_inlet_so2 = 359.0

        # Precalciner States
        self.pc_temp = self.cfg_kin.get("calcination", {}).get("nominal_pc_temperature_c", 907.0)
        self.pc_mid_temp = self.pc_temp - 11.0
        self.pc_calcination = self.cfg_dims.get("precalciner", {}).get("design_decarbonation_pct", 92.5)
        self.pc_press = 0.28

        # Tertiary Air Duct & Preheater
        tad = self.cfg_dims.get("tertiary_air_duct", {})
        self.tertiary_air_temp = tad.get("nominal_temperature_c", 862.0)
        self.tertiary_air_press = -3.6
        self.tad_damper = 99.0

        # Preheater Cyclones
        self.ph_top_gas_t = 413.0
        self.ph_top_draft = -56.0
        self.cyclone1N_gas_t = 432.0
        self.cyclone1N_meal_t = 458.0
        self.cyclone1N_press = -51.0
        self.cyclone1P_gas_t = 408.0
        self.cyclone1P_meal_t = 407.0
        self.cyclone1P_press = -50.0
        self.cyclone2N_t = 635.0
        self.cyclone2N_press = -39.0
        self.cyclone2P_t = 606.0
        self.cyclone2P_press = -31.0
        self.stage3_t = 762.0
        self.stage3_press = -9.6
        self.cyclone4N_t = 914.0
        self.cyclone4N_meal_t = 919.0
        self.cyclone4N_press = -18.0
        self.cyclone4P_t = 896.0
        self.cyclone4P_meal_t = 887.0
        self.cyclone4P_press = -17.0
        self.ph_o2 = 3.18
        self.ph_co = 0.310

        # Clinker Grate Cooler
        self.secondary_air_t = 1000.0
        self.kiln_hood_press = -0.30
        self.cooler_vent_t = 258.0
        self.cooler_filter_t = 89.0
        self.cooler_fan_current = 289.0
        self.cooler_fan_rpm = 908.0
        self.clinker_discharge_t = 90.0

        # Fuel Flow Rates (Nominal)
        cdr = self.cfg_fuels.get("cdr_alternative_fuel", {})
        pet = self.cfg_fuels.get("petcoke", {})
        oil = self.cfg_fuels.get("heavy_fuel_oil", {})
        self.pc_cdr_rate = cdr.get("nominal_pc_feed_tph", 10.66)
        self.pc_petcoke_rate = pet.get("nominal_pc_feed_tph", 3.68)
        self.kiln_petcoke_rate = pet.get("nominal_kiln_feed_tph", 6.15)
        self.kiln_cdr_rate = cdr.get("nominal_kiln_feed_tph", 2.44)
        self.kiln_oil_rate = oil.get("nominal_kiln_flow_l_h", 605.0)

        # Actuators
        self.id_fan_damper = 92.0
        self.cooler_vent_speed = 75.5

        # KPIs
        self.specific_heat_kcal = 775.6
        self.pc_thermal_split = 54.1
        self.alt_fuel_substitution = 41.5

        # Optimizer Interface Status
        self.optimizer_active = False
        self.opt_commands = {}

    def step(self, dt, control_actions=None, opt_commands=None):
        """
        Executes one dynamic first-principles integration step.
        If opt_commands contains Opt_Enable=True, optimization targets override base controls.
        """
        if control_actions is None:
            control_actions = {}
        if opt_commands is None:
            opt_commands = {}

        # 1. Check Optimizer Authority
        self.optimizer_active = bool(opt_commands.get("Opt_Enable", False))
        self.opt_commands = opt_commands

        # Extract Targets based on per-tag source (Local vs OPC UA)
        def resolve_sp(tag_id, default_local_val, opt_val):
            # 1. If optimizer supervisory authority is active, optimizer takes priority
            if self.optimizer_active and tag_id in opt_commands:
                return float(opt_commands[tag_id])
            # 2. If operator explicitly set local setpoint via DCS faceplate or API, respect it
            if tag_id in self.local_setpoints:
                return float(self.local_setpoints[tag_id])
            # 3. Otherwise check tag source
            tag_cfg = self.tag_dict_map.get(tag_id, {})
            source = tag_cfg.get("source", "local")
            if source == "opc_ua" and tag_id in opt_commands and self.optimizer_active:
                return float(opt_commands[tag_id])
            # Fallback to local default / action
            return default_local_val

        target_feed = resolve_sp("Opt_FeedRate_SP", control_actions.get("feed_rate", self.raw_meal_feed), opt_commands.get("Opt_FeedRate_SP", self.raw_meal_feed))
        target_pc_temp_sp = resolve_sp("Opt_PCTemp_SP", control_actions.get("pc_temp_sp", 907.0), opt_commands.get("Opt_PCTemp_SP", self.pc_temp))
        target_sinter_sp = resolve_sp("Opt_SinteringTemp_SP", control_actions.get("sinter_sp", 1450.0), opt_commands.get("Opt_SinteringTemp_SP", self.sintering_temp))
        kiln_fuel_bias = resolve_sp("Opt_KilnFuel_Bias_pct", 0.0, opt_commands.get("Opt_KilnFuel_Bias_pct", 0.0))
        pc_fuel_bias = resolve_sp("Opt_PCFuel_Bias_pct", 0.0, opt_commands.get("Opt_PCFuel_Bias_pct", 0.0))
        target_draft_sp = resolve_sp("Opt_PHTopDraft_SP", control_actions.get("draft_sp", -56.0), opt_commands.get("Opt_PHTopDraft_SP", self.ph_top_draft))
        target_hood_sp = resolve_sp("Opt_KilnHoodPress_SP", control_actions.get("hood_sp", -0.30), opt_commands.get("Opt_KilnHoodPress_SP", self.kiln_hood_press))
        target_tad_sp = resolve_sp("Opt_TADDamper_SP", control_actions.get("tad_sp", 99.0), opt_commands.get("Opt_TADDamper_SP", self.tad_damper))

        # 2. Raw Meal Feeder Response
        limits = self.cfg_raw.get("limits", {})
        min_feed = limits.get("min_feed_tph", 120.0)
        max_feed = limits.get("max_feed_tph", 360.0)
        tau_feeder = limits.get("feeder_time_constant_s", 1.5)
        clamped_feed_sp = max(min_feed, min(max_feed, target_feed))
        self.raw_meal_feed += (clamped_feed_sp - self.raw_meal_feed) * (dt / max(0.2, tau_feeder))

        # 3. Kiln Speed & Bed Transport Dynamics
        nom_speed = self.cfg_dims.get("rotary_kiln", {}).get("nominal_speed_rpm", 3.79)
        target_speed = nom_speed * (self.raw_meal_feed / self.nominal_feed)
        self.kiln_speed += (target_speed - self.kiln_speed) * (dt / 3.0)
        self.kiln_amps = 254.0 * (0.3 + 0.7 * (self.raw_meal_feed / self.nominal_feed))
        self.filling_degree = 10.96 * (self.raw_meal_feed / self.nominal_feed) / max(0.5, (self.kiln_speed / nom_speed))

        # Solids transit delay to clinker discharge (Saeman residence time ~ 26.8 min)
        transit_sec = self.cfg_dims.get("rotary_kiln", {}).get("solids_bed_transit_time_min", 26.8) * 60.0
        steady_clinker = self.raw_meal_feed / self.clinker_factor
        tau_bed = transit_sec / max(0.2, (self.kiln_speed / nom_speed))
        self.clinker_production += (steady_clinker - self.clinker_production) * (dt / tau_bed)

        # 4. Precalciner Fuel & Decarbonation Kinetics
        # Base fuel demand with feedforward trim + optimizer bias
        feed_ratio = self.raw_meal_feed / self.nominal_feed
        temp_err_pc = target_pc_temp_sp - self.pc_temp
        pc_fuel_op = 54.1 + (temp_err_pc * 0.25) + ((feed_ratio - 1.0) * 20.0) + pc_fuel_bias
        pc_fuel_op = max(20.0, min(100.0, pc_fuel_op))

        nom_cdr = self.cfg_fuels.get("cdr_alternative_fuel", {}).get("nominal_pc_feed_tph", 10.66)
        nom_pet = self.cfg_fuels.get("petcoke", {}).get("nominal_pc_feed_tph", 3.68)
        ratio_pc = pc_fuel_op / 54.1
        self.pc_cdr_rate = nom_cdr * ratio_pc
        self.pc_petcoke_rate = nom_pet * ratio_pc

        # Temperature response from fuel heating value & feed heat capacity
        target_pc_temp = 907.0 + (ratio_pc - 1.0) * 160.0 - (self.raw_meal_feed - self.nominal_feed) * 0.35 + (self.tertiary_air_temp - 862.0) * 0.15
        self.pc_temp += (target_pc_temp - self.pc_temp) * (dt / 4.0)
        self.pc_mid_temp = self.pc_temp - 11.0

        # Arrhenius Decarbonation Degree
        self.pc_calcination = 92.5 + 0.06 * (self.pc_temp - 907.0)
        self.pc_calcination = max(70.0, min(98.5, self.pc_calcination))

        # 5. Rotary Kiln Sintering & Free Lime Reactions
        temp_err_sinter = target_sinter_sp - self.sintering_temp
        kiln_fuel_op = 45.9 + (temp_err_sinter * 0.15) + ((feed_ratio - 1.0) * 12.0) + kiln_fuel_bias
        kiln_fuel_op = max(15.0, min(90.0, kiln_fuel_op))

        ratio_kiln = kiln_fuel_op / 45.9
        nom_kiln_pet = self.cfg_fuels.get("petcoke", {}).get("nominal_kiln_feed_tph", 6.15)
        nom_kiln_cdr = self.cfg_fuels.get("cdr_alternative_fuel", {}).get("nominal_kiln_feed_tph", 2.44)
        nom_kiln_oil = self.cfg_fuels.get("heavy_fuel_oil", {}).get("nominal_kiln_flow_l_h", 605.0)
        self.kiln_petcoke_rate = nom_kiln_pet * ratio_kiln
        self.kiln_cdr_rate = nom_kiln_cdr * ratio_kiln
        self.kiln_oil_rate = nom_kiln_oil * ratio_kiln

        target_sinter = 1450.0 + (ratio_kiln - 1.0) * 200.0 - (self.raw_meal_feed - self.nominal_feed) * 0.30 + (self.secondary_air_t - 1000.0) * 0.25
        self.sintering_temp += (target_sinter - self.sintering_temp) * (dt / 8.0)
        self.burning_zone_t1 = self.sintering_temp - 143.0
        self.burning_zone_t2 = self.sintering_temp - 133.0
        self.shell_temp = 280.0 + (self.sintering_temp - 1300.0) * 0.17

        # Free Lime Kinetics: Decay towards target based on sintering temperature & residence time
        tau_free_lime = self.cfg_kin.get("clinkerization", {}).get("free_lime_decay_time_constant_s", 60.0)
        target_free_lime = 1.30 - 0.015 * (self.sintering_temp - 1450.0) + 0.008 * (self.raw_meal_feed - self.nominal_feed)
        self.free_lime += (max(0.20, min(4.50, target_free_lime)) - self.free_lime) * (dt / max(5.0, tau_free_lime))

        # 6. Clinker Grate Cooler Heat Recuperation
        target_sec_air = 950.0 + (self.sintering_temp - 1400.0) * 0.8 - (self.raw_meal_feed - self.nominal_feed) * 0.15
        self.secondary_air_t += (target_sec_air - self.secondary_air_t) * (dt / 10.0)
        target_tert_air = 820.0 + (self.secondary_air_t - 950.0) * 0.65
        self.tertiary_air_temp += (target_tert_air - self.tertiary_air_temp) * (dt / 12.0)

        # Cooler Hood Draft (controlled to target_hood_sp)
        hood_err = target_hood_sp - self.kiln_hood_press
        self.cooler_vent_speed = max(20.0, min(100.0, 75.5 - hood_err * 25.0))
        self.cooler_fan_rpm = 908.0 * (self.cooler_vent_speed / 75.5)
        self.cooler_fan_current = 289.0 * math.pow(self.cooler_vent_speed / 75.5, 1.2)
        target_hood = target_hood_sp + ((self.raw_meal_feed - self.nominal_feed) / self.nominal_feed) * 0.3 - (self.cooler_vent_speed / 75.5 - 1.0) * 0.8
        self.kiln_hood_press += (target_hood - self.kiln_hood_press) * (dt / 0.8)

        # 7. Preheater Draft Network & Temperatures
        draft_err = target_draft_sp - self.ph_top_draft
        self.id_fan_damper = max(20.0, min(100.0, 92.0 - draft_err * 1.2))
        target_top_draft = -56.0 * math.pow(self.id_fan_damper / 92.0, 1.8) + ((self.raw_meal_feed - self.nominal_feed) / self.nominal_feed) * 5.0
        self.ph_top_draft += (target_top_draft - self.ph_top_draft) * (dt / 0.8)

        self.ph_top_gas_t = 413.0 + (self.pc_temp - 907.0) * 0.35 - (self.raw_meal_feed - self.nominal_feed) * 0.35
        self.cyclone1N_gas_t = self.ph_top_gas_t + 19.0
        self.cyclone1N_meal_t = self.cyclone1N_gas_t + 26.0
        self.cyclone1N_press = self.ph_top_draft + 5.0
        self.cyclone1P_gas_t = self.ph_top_gas_t - 5.0
        self.cyclone1P_meal_t = self.cyclone1P_gas_t - 1.0
        self.cyclone1P_press = self.ph_top_draft + 6.0

        self.stage3_t = 762.0 + (self.pc_temp - 907.0) * 0.7 - (self.raw_meal_feed - self.nominal_feed) * 0.20
        self.stage3_press = self.ph_top_draft + 46.4
        self.cyclone2N_t = 635.0 + (self.stage3_t - 762.0) * 0.65
        self.cyclone2N_press = self.ph_top_draft + 17.0
        self.cyclone2P_t = 606.0 + (self.stage3_t - 762.0) * 0.65
        self.cyclone2P_press = self.ph_top_draft + 25.0

        self.cyclone4N_t = self.pc_temp + 7.0
        self.cyclone4N_meal_t = self.pc_temp + 12.0
        self.cyclone4N_press = self.ph_top_draft + 38.0
        self.cyclone4P_t = self.pc_temp - 11.0
        self.cyclone4P_meal_t = self.pc_temp - 20.0
        self.cyclone4P_press = self.ph_top_draft + 39.0

        # 8. Gas Analyzers (O2, CO, NOx, SO2)
        target_kln_o2 = 2.32 - (ratio_kiln - 1.0) * 2.2 + (self.secondary_air_t - 1000.0) * 0.005
        self.kiln_inlet_o2 += (max(0.5, min(8.0, target_kln_o2)) - self.kiln_inlet_o2) * (dt / 4.0)
        self.ph_o2 = self.kiln_inlet_o2 + 0.86 * (target_tad_sp / 99.0)
        self.ph_co = max(0.02, min(3.50, 0.310 - (self.ph_o2 - 3.18) * 0.12))
        self.kiln_inlet_nox = 857.0 * math.exp(0.0035 * (self.sintering_temp - 1450.0))
        self.kiln_inlet_so2 = 359.0 + (self.kiln_petcoke_rate - 6.15) * 45.0

        # 9. Master KPIs & Thermal Consumption
        cdr_lhv = self.cfg_fuels.get("cdr_alternative_fuel", {}).get("lhv_mj_kg", 18.0)
        pet_lhv = self.cfg_fuels.get("petcoke", {}).get("lhv_mj_kg", 31.4)
        oil_lhv = self.cfg_fuels.get("heavy_fuel_oil", {}).get("lhv_mj_kg", 41.8)
        oil_density = self.cfg_fuels.get("heavy_fuel_oil", {}).get("density_kg_liter", 0.95)

        pc_energy_gj = self.pc_cdr_rate * cdr_lhv + self.pc_petcoke_rate * pet_lhv
        kiln_energy_gj = self.kiln_petcoke_rate * pet_lhv + self.kiln_cdr_rate * cdr_lhv + (self.kiln_oil_rate * oil_density * oil_lhv / 1000.0)
        total_energy_gj = pc_energy_gj + kiln_energy_gj
        alt_energy_gj = (self.pc_cdr_rate + self.kiln_cdr_rate) * cdr_lhv

        self.pc_thermal_split = (pc_energy_gj / max(1.0, total_energy_gj)) * 100.0
        self.alt_fuel_substitution = (alt_energy_gj / max(1.0, total_energy_gj)) * 100.0
        self.specific_heat_kcal = (total_energy_gj * 1e6 / 4.1868) / (max(10.0, self.clinker_production) * 1000.0)

    def get_telemetry_dict(self):
        """Returns complete plant state dictionary matching OPC UA Feedback nodes and HMI tags."""
        return {
            "K3F07_FeedRate_tph": round(self.raw_meal_feed, 2),
            "ClinkerProduction_tph": round(self.clinker_production, 2),
            "SpecificHeat_kcal_kg": round(self.specific_heat_kcal, 1),
            "K3T62A_PrecalcinerTemp_C": round(self.pc_temp, 1),
            "TERMO_SinteringTemp_C": round(self.sintering_temp, 1),
            "CalLivre_FreeLime_pct": round(self.free_lime, 3),
            "K3P02_PHTopDraft_mbar": round(self.ph_top_draft, 1),
            "L3P311_KilnHoodPress_mbar": round(self.kiln_hood_press, 2),
            "K3Q01_KilnInletO2_pct": round(self.kiln_inlet_o2, 2),
            "K3Q07_KilnInletNOx_ppm": round(self.kiln_inlet_nox, 0),
            "K3Q02_PHTopO2_pct": round(self.ph_o2, 2),
            "K3Q03_PHTopCO_pct": round(self.ph_co, 3),
            "L3S01_KilnSpeed_rpm": round(self.kiln_speed, 2),
            "L3I01_KilnDriveAmp_A": round(self.kiln_amps, 0),
            "K3T60_TertiaryAirTemp_C": round(self.tertiary_air_temp, 1),
            "L3T305_SecondaryAirTemp_C": round(self.secondary_air_t, 1),
            "L3T324_CoolerVentTemp_C": round(self.cooler_vent_t, 1),
            "PCDecarbonation_pct": round(self.pc_calcination, 2),
            "OptimizerActive": self.optimizer_active,
            "PCThermalSplit_pct": round(self.pc_thermal_split, 1),
            "AltFuelSubst_pct": round(self.alt_fuel_substitution, 1),
            "KilnFilling_pct": round(self.filling_degree, 2),
            "K3T17_Cycl1N_GasT": round(self.cyclone1N_gas_t, 1),
            "K3T18_Cycl1P_GasT": round(self.cyclone1P_gas_t, 1),
            "K3T50_Cycl2N_Temp": round(self.cyclone2N_t, 1),
            "K3T51_Cycl2P_Temp": round(self.cyclone2P_t, 1),
            "K3T52_Stage3_Temp": round(self.stage3_t, 1),
            "K3T22_Cycl4N_GasT": round(self.cyclone4N_t, 1),
            "K3T23_Cycl4P_GasT": round(self.cyclone4P_t, 1),
            "K3T16_PHTopGasTemp_C": round(self.ph_top_gas_t, 1)
        }

    def get_tags_list(self):
        """Returns unified tag list with live values, sources, and status."""
        telemetry = self.get_telemetry_dict()
        tags_out = []
        for t in self.cfg.get("tag_dictionary", []):
            t_copy = dict(t)
            tid = t["tag_id"]
            if t["category"] == "setpoint":
                if tid in self.local_setpoints:
                    t_copy["value"] = round(self.local_setpoints[tid], 2)
                elif tid in self.opt_commands and t.get("source") == "opc_ua":
                    t_copy["value"] = round(float(self.opt_commands[tid]), 2)
                else:
                    t_copy["value"] = round(float(t.get("default", 0.0)), 2)
            elif t["category"] == "measurement":
                if tid in telemetry:
                    t_copy["value"] = telemetry[tid]
                elif tid in self.custom_tag_values:
                    t_copy["value"] = round(self.custom_tag_values[tid], 2)
                else:
                    t_copy["value"] = round(float(t.get("default", 0.0)), 2)
            else:
                t_copy["value"] = round(float(self.custom_tag_values.get(tid, t.get("default", 0.0))), 2)

            # Determine quality / connectivity indicator
            if t.get("source") == "opc_ua":
                t_copy["status"] = "OPC_BOUND"
            else:
                t_copy["status"] = "LOCAL_SIM"

            tags_out.append(t_copy)
        return tags_out

    def set_tag_source(self, tag_id, source):
        """Sets a tag's source to 'local' or 'opc_ua' and persists to plant_config.json."""
        for t in self.cfg.get("tag_dictionary", []):
            if t["tag_id"] == tag_id:
                t["source"] = source
                self.tag_dict_map[tag_id] = t
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2)
                return True
        return False

    def set_tag_value(self, tag_id, value):
        """Sets a local setpoint or overrides a measurement value."""
        val_float = float(value)
        for t in self.cfg.get("tag_dictionary", []):
            if t["tag_id"] == tag_id:
                if t["category"] == "setpoint":
                    self.local_setpoints[tag_id] = val_float
                    if tag_id == "Opt_FeedRate_SP":
                        self.raw_meal_feed = val_float
                    elif tag_id == "Opt_PCTemp_SP":
                        self.pc_temp = val_float
                    elif tag_id == "Opt_SinteringTemp_SP":
                        self.sintering_temp = val_float
                    elif tag_id == "Opt_PHTopDraft_SP":
                        self.ph_top_draft = val_float
                    elif tag_id == "Opt_KilnHoodPress_SP":
                        self.kiln_hood_press = val_float
                else:
                    self.custom_tag_values[tag_id] = val_float
                return True
        return False

    def apply_operator_setpoint(self, loop_or_tag, value):
        """Applies an operator setpoint from Web DCS faceplate or API."""
        val = float(value)
        mapping = {
            "feed": "Opt_FeedRate_SP",
            "Opt_FeedRate_SP": "Opt_FeedRate_SP",
            "tic_pc": "Opt_PCTemp_SP",
            "Opt_PCTemp_SP": "Opt_PCTemp_SP",
            "tic_bz": "Opt_SinteringTemp_SP",
            "Opt_SinteringTemp_SP": "Opt_SinteringTemp_SP",
            "pic_ph": "Opt_PHTopDraft_SP",
            "Opt_PHTopDraft_SP": "Opt_PHTopDraft_SP",
            "pic_kh": "Opt_KilnHoodPress_SP",
            "Opt_KilnHoodPress_SP": "Opt_KilnHoodPress_SP",
            "aic_o2": "Opt_TADDamper_SP",
            "Opt_TADDamper_SP": "Opt_TADDamper_SP",
            "Opt_KilnFuel_Bias_pct": "Opt_KilnFuel_Bias_pct",
            "Opt_PCFuel_Bias_pct": "Opt_PCFuel_Bias_pct"
        }
        tag_id = mapping.get(loop_or_tag, loop_or_tag)
        self.local_setpoints[tag_id] = val
        logger.info(f"Operator setpoint applied: {loop_or_tag} ({tag_id}) -> {val}")
        return True

    def update_tag(self, tag_id, updates):
        """Updates tag metadata such as opc_node_id, direction, name, etc."""
        for t in self.cfg.get("tag_dictionary", []):
            if t["tag_id"] == tag_id:
                t.update(updates)
                self.tag_dict_map[tag_id] = t
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2)
                return True
        return False

    def add_custom_tag(self, tag_data):
        """Adds a new custom tag and saves to plant_config.json."""
        if "tag_dictionary" not in self.cfg:
            self.cfg["tag_dictionary"] = []
        for t in self.cfg["tag_dictionary"]:
            if t["tag_id"] == tag_data["tag_id"]:
                t.update(tag_data)
                self.tag_dict_map[tag_data["tag_id"]] = t
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2)
                return True
        tag_data["is_custom"] = True
        self.cfg["tag_dictionary"].append(tag_data)
        self.tag_dict_map[tag_data["tag_id"]] = tag_data
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)
        return True

    def delete_custom_tag(self, tag_id):
        """Removes a custom tag."""
        if "tag_dictionary" in self.cfg:
            self.cfg["tag_dictionary"] = [t for t in self.cfg["tag_dictionary"] if t["tag_id"] != tag_id]
            self.tag_dict_map.pop(tag_id, None)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2)
            return True
        return False

    def get_flowsheet_data(self):
        """
        Computes dynamic process flowsheet state: 25 numbered process streams,
        equipment operating status, and runtime mass & thermal energy balances.
        """
        feed = self.raw_meal_feed
        clinker = self.clinker_production
        feed_ratio = feed / max(1.0, self.nominal_feed)
        clinker_ratio = clinker / max(1.0, self.nominal_clinker)

        # Fuel Flow Rates
        pc_cdr = self.pc_cdr_rate
        pc_pet = self.pc_petcoke_rate
        kiln_pet = self.kiln_petcoke_rate
        kiln_cdr = self.kiln_cdr_rate
        kiln_oil_tph = (self.kiln_oil_rate * 0.93) / 1000.0  # 605 L/h ~ 0.56 t/h

        # Air Flow Rates
        primary_air_tph = 9.30
        primary_air_nm3h = 7200.0
        sec_air_tph = 84.30 * feed_ratio
        sec_air_nm3h = 67800.0 * feed_ratio
        tert_air_tph = 128.40 * feed_ratio
        tert_air_nm3h = 103500.0 * feed_ratio
        cooling_air_tph = 348.50 * feed_ratio
        cooling_air_nm3h = 270000.0 * feed_ratio

        # Gas Flows
        kiln_flue_gas_tph = 96.22 * feed_ratio
        kiln_flue_gas_nm3h = 72400.0 * feed_ratio
        pc_gas_tph = 205.30 * feed_ratio
        pc_gas_nm3h = 154500.0 * feed_ratio
        ph_top_gas_tph = 378.20 * feed_ratio
        ph_top_gas_nm3h = 268500.0 * feed_ratio
        cooler_vent_tph = 135.80 * feed_ratio
        cooler_vent_nm3h = 105200.0 * feed_ratio
        dust_loss_tph = 4.80 * feed_ratio
        clinker_silo_tph = clinker - (dust_loss_tph * 0.1)

        # Enthalpy conversion helper (t/h, cp_kcal_kg_c, temp_c -> GJ/h)
        def calc_h_solid(mass_tph, temp_c, cp_kcal=0.22):
            return mass_tph * cp_kcal * (temp_c + 273.15) * 4.184 / 1000.0

        def calc_h_gas(mass_tph, temp_c, cp_kcal=0.25):
            return mass_tph * cp_kcal * (temp_c + 273.15) * 4.184 / 1000.0

        # Fuel Enthalpies (Chemical LHV in GJ/h)
        cdr_lhv_gj_t = self.cfg_fuels.get("cdr_alternative_fuel", {}).get("lhv_mj_kg", 18.0)
        pet_lhv_gj_t = self.cfg_fuels.get("petcoke", {}).get("lhv_mj_kg", 31.4)
        oil_lhv_gj_t = self.cfg_fuels.get("heavy_fuel_oil", {}).get("lhv_mj_kg", 41.8)

        # 25 Process Streams
        streams = [
            {
                "id": 1,
                "name": "Raw Meal Total Feed",
                "phase": "Solid",
                "from": "Meal Silo Elevator",
                "to": "Preheater Tower Top",
                "mass_tph": round(feed, 2),
                "nm3h": None,
                "temp_c": 60.0,
                "press_mbar": 0.0,
                "enthalpy_gjh": round(calc_h_solid(feed, 60.0, 0.21), 2),
                "composition": "CaCO3: 76.85%, SiO2: 13.5%, LOI: 35.3%"
            },
            {
                "id": 2,
                "name": "Raw Meal String N Feed",
                "phase": "Solid",
                "from": "Meal Feed Splitter",
                "to": "Gas Riser 1N-2N",
                "mass_tph": round(feed * 0.5, 2),
                "nm3h": None,
                "temp_c": 60.0,
                "press_mbar": round(self.cyclone2N_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.5, 60.0, 0.21), 2),
                "composition": "50% raw meal split to North string"
            },
            {
                "id": 3,
                "name": "Raw Meal String P Feed",
                "phase": "Solid",
                "from": "Meal Feed Splitter",
                "to": "Gas Riser 1P-2P",
                "mass_tph": round(feed * 0.5, 2),
                "nm3h": None,
                "temp_c": 60.0,
                "press_mbar": round(self.cyclone2P_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.5, 60.0, 0.21), 2),
                "composition": "50% raw meal split to South string"
            },
            {
                "id": 4,
                "name": "Cyclone 1N Meal Exit",
                "phase": "Solid",
                "from": "Cyclone 1N Dipleg",
                "to": "Riser Duct to 2N",
                "mass_tph": round(feed * 0.499, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone1N_meal_t, 1),
                "press_mbar": round(self.cyclone1N_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.499, self.cyclone1N_meal_t, 0.22), 2),
                "composition": "Preheated raw meal, moisture evaporated"
            },
            {
                "id": 5,
                "name": "Cyclone 1P Meal Exit",
                "phase": "Solid",
                "from": "Cyclone 1P Dipleg",
                "to": "Riser Duct to 2P",
                "mass_tph": round(feed * 0.499, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone1P_meal_t, 1),
                "press_mbar": round(self.cyclone1P_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.499, self.cyclone1P_meal_t, 0.22), 2),
                "composition": "Preheated raw meal, moisture evaporated"
            },
            {
                "id": 6,
                "name": "Cyclone 2N Meal Exit",
                "phase": "Solid",
                "from": "Cyclone 2N Dipleg",
                "to": "Stage 3 Chamber Riser",
                "mass_tph": round(feed * 0.498, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone2N_t, 1),
                "press_mbar": round(self.cyclone2N_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.498, self.cyclone2N_t, 0.23), 2),
                "composition": "Partially dehydroxylated clay minerals"
            },
            {
                "id": 7,
                "name": "Cyclone 2P Meal Exit",
                "phase": "Solid",
                "from": "Cyclone 2P Dipleg",
                "to": "Stage 3 Chamber Riser",
                "mass_tph": round(feed * 0.498, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone2P_t, 1),
                "press_mbar": round(self.cyclone2P_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.498, self.cyclone2P_t, 0.23), 2),
                "composition": "Partially dehydroxylated clay minerals"
            },
            {
                "id": 8,
                "name": "Stage 3 Meal Outflow",
                "phase": "Solid",
                "from": "Stage 3 Cyclone Dipleg",
                "to": "Precalciner Chamber",
                "mass_tph": round(feed * 0.995, 2),
                "nm3h": None,
                "temp_c": round(self.stage3_t, 1),
                "press_mbar": round(self.stage3_press, 1),
                "enthalpy_gjh": round(calc_h_solid(feed * 0.995, self.stage3_t, 0.24), 2),
                "composition": "Meal ready for calcination (12.5% pre-decarb)"
            },
            {
                "id": 9,
                "name": "Precalciner CDR Fuel",
                "phase": "Solid",
                "from": "Feeder Z3N218 / 213",
                "to": "Precalciner Lower Burners",
                "mass_tph": round(pc_cdr, 2),
                "nm3h": None,
                "temp_c": 25.0,
                "press_mbar": 0.0,
                "enthalpy_gjh": round(pc_cdr * cdr_lhv_gj_t, 2),
                "composition": "RDF/CDR, LHV=18.0 MJ/kg, Ash=11.3%, H2O=14%"
            },
            {
                "id": 10,
                "name": "Precalciner Petcoke Fuel",
                "phase": "Solid",
                "from": "Feeder S3F04",
                "to": "Precalciner Burners",
                "mass_tph": round(pc_pet, 2),
                "nm3h": None,
                "temp_c": 65.0,
                "press_mbar": 0.0,
                "enthalpy_gjh": round(pc_pet * pet_lhv_gj_t, 2),
                "composition": "Petcoke, LHV=31.4 MJ/kg, S=5.5%, VM=10.2%"
            },
            {
                "id": 11,
                "name": "Tertiary Air to PC",
                "phase": "Gas",
                "from": "Cooler Tertiary Duct Takeoff",
                "to": "Precalciner Combustion Bottom",
                "mass_tph": round(tert_air_tph, 2),
                "nm3h": round(tert_air_nm3h, 0),
                "temp_c": round(self.tertiary_air_temp, 1),
                "press_mbar": round(self.tertiary_air_press, 1),
                "enthalpy_gjh": round(calc_h_gas(tert_air_tph, self.tertiary_air_temp, 0.26), 2),
                "composition": "O2: 20.7%, N2: 78.4%, CO2: 0.04%"
            },
            {
                "id": 12,
                "name": "Kiln Flue Gas to PC Riser",
                "phase": "Gas",
                "from": "Kiln Smoke Chamber / Inlet",
                "to": "Precalciner Bottom Riser",
                "mass_tph": round(kiln_flue_gas_tph, 2),
                "nm3h": round(kiln_flue_gas_nm3h, 0),
                "temp_c": round(self.kiln_inlet_temp, 1),
                "press_mbar": round(self.kiln_inlet_press, 1),
                "enthalpy_gjh": round(calc_h_gas(kiln_flue_gas_tph, self.kiln_inlet_temp, 0.28), 2),
                "composition": f"CO2: 24.8%, O2: {self.kiln_inlet_o2:.2f}%, NOx: {self.kiln_inlet_nox:.0f} ppm"
            },
            {
                "id": 13,
                "name": "PC Exit Gas + Meal Suspension",
                "phase": "2-Phase",
                "from": "Precalciner Vessel Top",
                "to": "Cyclones 4N & 4P",
                "mass_tph": round(pc_gas_tph + (clinker * 1.042), 2),
                "nm3h": round(pc_gas_nm3h, 0),
                "temp_c": round(self.pc_temp, 1),
                "press_mbar": round(self.pc_press, 1),
                "enthalpy_gjh": round(calc_h_gas(pc_gas_tph, self.pc_temp, 0.27) + calc_h_solid(clinker * 1.042, self.pc_temp, 0.26), 2),
                "composition": f"Decarbonation: {self.pc_calcination:.1f}%, CO2: 33.2%"
            },
            {
                "id": 14,
                "name": "Cyclone 4N Calcined Meal",
                "phase": "Solid",
                "from": "Cyclone 4N Dipleg",
                "to": "Kiln Inlet Feeding Shelf",
                "mass_tph": round(clinker * 0.521, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone4N_meal_t, 1),
                "press_mbar": round(self.cyclone4N_press, 1),
                "enthalpy_gjh": round(calc_h_solid(clinker * 0.521, self.cyclone4N_meal_t, 0.26), 2),
                "composition": f"CaO: 66.8%, Decarb: {self.pc_calcination:.1f}%"
            },
            {
                "id": 15,
                "name": "Cyclone 4P Calcined Meal",
                "phase": "Solid",
                "from": "Cyclone 4P Dipleg",
                "to": "Kiln Inlet Feeding Shelf",
                "mass_tph": round(clinker * 0.521, 2),
                "nm3h": None,
                "temp_c": round(self.cyclone4P_meal_t, 1),
                "press_mbar": round(self.cyclone4P_press, 1),
                "enthalpy_gjh": round(calc_h_solid(clinker * 0.521, self.cyclone4P_meal_t, 0.26), 2),
                "composition": f"CaO: 66.8%, Decarb: {self.pc_calcination:.1f}%"
            },
            {
                "id": 16,
                "name": "Kiln Main Petcoke Fuel",
                "phase": "Solid",
                "from": "Feeder L3F200",
                "to": "Kiln Main Burner Pipe",
                "mass_tph": round(kiln_pet, 2),
                "nm3h": None,
                "temp_c": 65.0,
                "press_mbar": 0.0,
                "enthalpy_gjh": round(kiln_pet * pet_lhv_gj_t, 2),
                "composition": "Petcoke, LHV=31.4 MJ/kg, 86.5% C"
            },
            {
                "id": 17,
                "name": "Kiln Main CDR Fuel",
                "phase": "Solid",
                "from": "Feeder Z3N412",
                "to": "Kiln Main Burner Lance",
                "mass_tph": round(kiln_cdr, 2),
                "nm3h": None,
                "temp_c": 25.0,
                "press_mbar": 0.0,
                "enthalpy_gjh": round(kiln_cdr * cdr_lhv_gj_t, 2),
                "composition": "Alternative fuel CDR, LHV=18.0 MJ/kg"
            },
            {
                "id": 18,
                "name": "Kiln Heavy Fuel Oil Trim",
                "phase": "Liquid",
                "from": "HFO Metering Rack L3F03",
                "to": "Kiln Main Burner Central Gun",
                "mass_tph": round(kiln_oil_tph, 2),
                "nm3h": None,
                "temp_c": 85.0,
                "press_mbar": 18000.0,
                "enthalpy_gjh": round(kiln_oil_tph * oil_lhv_gj_t, 2),
                "composition": "Heavy Fuel Oil, LHV=41.8 MJ/kg (605 L/h)"
            },
            {
                "id": 19,
                "name": "Secondary Air to Kiln",
                "phase": "Gas",
                "from": "Cooler Recuperating Grate",
                "to": "Kiln Hood / Flame Zone",
                "mass_tph": round(sec_air_tph, 2),
                "nm3h": round(sec_air_nm3h, 0),
                "temp_c": round(self.secondary_air_t, 1),
                "press_mbar": round(self.kiln_hood_press, 2),
                "enthalpy_gjh": round(calc_h_gas(sec_air_tph, self.secondary_air_t, 0.27), 2),
                "composition": "Preheated combustion air, O2: 20.6%, N2: 78.5%"
            },
            {
                "id": 20,
                "name": "Primary Air to Burner",
                "phase": "Gas",
                "from": "Primary High-Pressure Blower",
                "to": "Kiln Burner Momentum Nozzles",
                "mass_tph": round(primary_air_tph, 2),
                "nm3h": round(primary_air_nm3h, 0),
                "temp_c": 35.0,
                "press_mbar": 120.0,
                "enthalpy_gjh": 0.42,
                "composition": "Axial/Radial flame momentum air (9% total)"
            },
            {
                "id": 21,
                "name": "Clinker Discharged from Kiln",
                "phase": "Solid",
                "from": "Kiln Sintering Bed",
                "to": "Grate Cooler Inlet Bullnose",
                "mass_tph": round(clinker, 2),
                "nm3h": None,
                "temp_c": 1350.0,
                "press_mbar": round(self.kiln_hood_press, 2),
                "enthalpy_gjh": round(calc_h_solid(clinker, 1350.0, 0.27), 2),
                "composition": f"C3S: 61.2%, C2S: 16.5%, Free CaO: {self.free_lime:.2f}%"
            },
            {
                "id": 22,
                "name": "Cooler Ambient Aeration Air",
                "phase": "Gas",
                "from": "Cooling Fans 1 to 6",
                "to": "Cooler Undergrate Chambers",
                "mass_tph": round(cooling_air_tph, 2),
                "nm3h": round(cooling_air_nm3h, 0),
                "temp_c": 25.0,
                "press_mbar": 65.0,
                "enthalpy_gjh": round(calc_h_gas(cooling_air_tph, 25.0, 0.24), 2),
                "composition": "Ambient aeration air, 2.05 kg air / kg clinker"
            },
            {
                "id": 23,
                "name": "Clinker Product to Silo",
                "phase": "Solid",
                "from": "Clinker Grate Discharge Crusher",
                "to": "Transport Deep Bucket Elevator",
                "mass_tph": round(clinker_silo_tph, 2),
                "nm3h": None,
                "temp_c": round(self.clinker_discharge_t, 1),
                "press_mbar": 0.0,
                "enthalpy_gjh": round(calc_h_solid(clinker_silo_tph, self.clinker_discharge_t, 0.21), 2),
                "composition": f"Quality C3S: 61.5%, Free Lime: {self.free_lime:.2f}%"
            },
            {
                "id": 24,
                "name": "Cooler Excess Vent Air",
                "phase": "Gas",
                "from": "Cooler Quenching Hood",
                "to": "Dedusting Baghouse Filter & Stack",
                "mass_tph": round(cooler_vent_tph, 2),
                "nm3h": round(cooler_vent_nm3h, 0),
                "temp_c": round(self.cooler_vent_t, 1),
                "press_mbar": -4.6,
                "enthalpy_gjh": round(calc_h_gas(cooler_vent_tph, self.cooler_vent_t, 0.25), 2),
                "composition": "Clean cooling excess air, O2: 20.8%, N2: 78.5%"
            },
            {
                "id": 25,
                "name": "Preheater Combined Top Gas",
                "phase": "Gas",
                "from": "Cyclones 1N & 1P Top Ducts",
                "to": "Conditioning Tower & ID Fan",
                "mass_tph": round(ph_top_gas_tph, 2),
                "nm3h": round(ph_top_gas_nm3h, 0),
                "temp_c": round(self.ph_top_gas_t, 1),
                "press_mbar": round(self.ph_top_draft, 1),
                "enthalpy_gjh": round(calc_h_gas(ph_top_gas_tph, self.ph_top_gas_t, 0.26), 2),
                "composition": f"CO2: 29.8%, O2: {self.ph_o2:.2f}%, CO: {self.ph_co:.3f}%, H2O: 9.6%"
            }
        ]

        # Global Mass Balance Audit
        total_inflow = feed + pc_cdr + pc_pet + kiln_pet + kiln_cdr + kiln_oil_tph + primary_air_tph + cooling_air_tph
        total_outflow = clinker + ph_top_gas_tph + cooler_vent_tph + dust_loss_tph

        # Global Thermal Energy Audit
        total_fuel_gj = (pc_cdr * cdr_lhv_gj_t) + (pc_pet * pet_lhv_gj_t) + (kiln_pet * pet_lhv_gj_t) + (kiln_cdr * cdr_lhv_gj_t) + (kiln_oil_tph * oil_lhv_gj_t)
        total_heat_in_gj = total_fuel_gj + calc_h_solid(feed, 60.0) + calc_h_gas(cooling_air_tph, 25.0) + 0.42
        
        calcination_gj = feed * 0.7685 * 1.785  # CaCO3 endothermic decarbonation heat
        clinker_formation_credit = clinker * -0.104  # Exothermic alite formation
        top_gas_heat_gj = calc_h_gas(ph_top_gas_tph, self.ph_top_gas_t)
        cooler_vent_heat_gj = calc_h_gas(cooler_vent_tph, self.cooler_vent_t)
        clinker_sensible_gj = calc_h_solid(clinker, self.clinker_discharge_t)
        shell_losses_gj = 22.8 + 18.2 + 9.5  # Kiln, calciner & cooler radiation/convection
        total_heat_out_gj = calcination_gj + clinker_formation_credit + top_gas_heat_gj + cooler_vent_heat_gj + clinker_sensible_gj + shell_losses_gj

        return {
            "timestamp": time.time(),
            "streams": streams,
            "mass_balance": {
                "inflows": {
                    "raw_meal_feed": round(feed, 2),
                    "pc_cdr_fuel": round(pc_cdr, 2),
                    "pc_petcoke_fuel": round(pc_pet, 2),
                    "kiln_petcoke_fuel": round(kiln_pet, 2),
                    "kiln_cdr_fuel": round(kiln_cdr, 2),
                    "kiln_hfo_trim": round(kiln_oil_tph, 2),
                    "primary_air": round(primary_air_tph, 2),
                    "cooling_aeration_air": round(cooling_air_tph, 2)
                },
                "outflows": {
                    "clinker_product": round(clinker, 2),
                    "preheater_top_gas": round(ph_top_gas_tph, 2),
                    "cooler_excess_vent": round(cooler_vent_tph, 2),
                    "dust_filter_return": round(dust_loss_tph, 2)
                },
                "total_inflow_tph": round(total_inflow, 2),
                "total_outflow_tph": round(total_outflow, 2),
                "closure_pct": round((total_outflow / max(0.1, total_inflow)) * 100.0, 2),
                "error_tph": round(total_outflow - total_inflow, 2)
            },
            "heat_balance": {
                "fuel_energy_gjh": round(total_fuel_gj, 2),
                "fuel_power_mw": round(total_fuel_gj / 3.6, 2),
                "specific_heat_kcal_kg": round(self.specific_heat_kcal, 1),
                "total_heat_in_gjh": round(total_heat_in_gj, 2),
                "total_heat_consumed_gjh": round(total_heat_out_gj, 2),
                "calcination_enthalpy_gjh": round(calcination_gj, 2),
                "clinker_formation_credit_gjh": round(clinker_formation_credit, 2),
                "preheater_top_gas_heat_gjh": round(top_gas_heat_gj, 2),
                "cooler_vent_heat_gjh": round(cooler_vent_heat_gj, 2),
                "clinker_sensible_heat_gjh": round(clinker_sensible_gj, 2),
                "shell_radiation_convection_gjh": round(shell_losses_gj, 2)
            }
        }

