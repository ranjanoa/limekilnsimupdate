"""
Pre-built Modular Flowsheet Templates:
1. kiln_3_pyroprocess: Complete 5-Stage Kiln 3 Pyroprocessing Plant (280 t/h raw meal, 175 t/h clinker)
2. single_cyclone_demo: Minimal test flowsheet for learning and component validation
3. calciner_combustion_loop: Precalciner with tertiary air and fuel burner
4. lime_kiln_calciner: Rotary Lime Kiln decarbonation system
"""

from typing import Dict, Any, List
from .flowsheet_graph import FlowsheetGraph
from .library import get_block_class


def get_template_manifest() -> List[Dict[str, str]]:
    """Returns list of pre-built template metadata."""
    return [
        {
            "id": "kiln_3_pyroprocess",
            "name": "Kiln 3 Full Pyroprocessing Plant (280 TPH)",
            "description": "5-stage suspension preheater string, inline calciner, tertiary air duct, 72m rotary kiln, and hydraulic grate cooler.",
            "components_count": 13,
            "streams_count": 20,
        },
        {
            "id": "single_cyclone_demo",
            "name": "Single Cyclone Preheater Test Loop",
            "description": "Minimal flowsheet demonstrating gas-solid counter-current thermal exchange and centrifugal collection.",
            "components_count": 5,
            "streams_count": 4,
        },
        {
            "id": "calciner_combustion_loop",
            "name": "Precalciner Combustion & Decarbonation Loop",
            "description": "Arrhenius decarbonation kinetics, multi-fuel combustion, tertiary air takeoff, and bottom separation stage.",
            "components_count": 7,
            "streams_count": 7,
        },
        {
            "id": "dual_fuel_calciner_rdf",
            "name": "Calciner Multi-Fuel Co-Firing (Coal + RDF Sum Node)",
            "description": "Precalciner co-firing primary coal and Refuse-Derived Fuel (RDF) blended via FuelMixer sum node with online TSR% tracking.",
            "components_count": 9,
            "streams_count": 8,
        },
        {
            "id": "lime_kiln_calciner",
            "name": "Rotary Lime Kiln Quicklime Production",
            "description": "High-calcium limestone calcination to quicklime (CaO) with cooler heat recuperation.",
            "components_count": 6,
            "streams_count": 6,
        },
    ]


def build_kiln3_pyroprocess_template() -> Dict[str, Any]:
    """Generates the full Kiln 3 cement pyroprocessing plant flowsheet JSON."""
    return {
        "flowsheet_id": "kiln_3_pyroprocess",
        "name": "Kiln 3 Full Pyroprocessing Plant (280 TPH)",
        "version": "2.0",
        "description": "Complete 5-stage preheater, inline calciner, tertiary air duct, rotary kiln, and grate cooler.",
        "components": [
            {
                "id": "FEED_01",
                "name": "Raw Meal Feeder",
                "type": "GravimetricFeeder",
                "position": {"x": 60, "y": 60},
                "parameters": {"nominal_rate_tph": 280.0, "temperature_c": 60.0, "time_constant_s": 1.5},
            },
            {
                "id": "CYC_01",
                "name": "Preheater Cyclone C1 (Top)",
                "type": "CycloneStage",
                "position": {"x": 260, "y": 60},
                "parameters": {"stage_number": 1, "separation_efficiency": 0.985, "thermal_effectiveness": 0.85, "dp_mbar": 5.0},
            },
            {
                "id": "CYC_02",
                "name": "Preheater Cyclone C2",
                "type": "CycloneStage",
                "position": {"x": 260, "y": 180},
                "parameters": {"stage_number": 2, "separation_efficiency": 0.985, "thermal_effectiveness": 0.82, "dp_mbar": 5.5},
            },
            {
                "id": "CYC_03",
                "name": "Preheater Cyclone C3",
                "type": "CycloneStage",
                "position": {"x": 260, "y": 300},
                "parameters": {"stage_number": 3, "separation_efficiency": 0.985, "thermal_effectiveness": 0.80, "dp_mbar": 5.5},
            },
            {
                "id": "CYC_04",
                "name": "Preheater Cyclone C4",
                "type": "CycloneStage",
                "position": {"x": 260, "y": 420},
                "parameters": {"stage_number": 4, "separation_efficiency": 0.985, "thermal_effectiveness": 0.78, "dp_mbar": 5.8},
            },
            {
                "id": "CALC_01",
                "name": "Inline Precalciner Reactor",
                "type": "CalcinerReactor",
                "position": {"x": 480, "y": 420},
                "parameters": {"volume_m3": 1100.0, "design_calcination_pct": 92.5, "target_temp_c": 865.0},
            },
            {
                "id": "FUEL_PC",
                "name": "Precalciner Fuel Dosing",
                "type": "FuelFeeder",
                "position": {"x": 480, "y": 570},
                "parameters": {"fuel_name": "Petcoke & CDR", "nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
            },
            {
                "id": "CYC_05",
                "name": "Preheater Cyclone C5 (Bottom)",
                "type": "CycloneStage",
                "position": {"x": 680, "y": 360},
                "parameters": {"stage_number": 5, "separation_efficiency": 0.985, "thermal_effectiveness": 0.82, "dp_mbar": 5.0},
            },
            {
                "id": "KILN_01",
                "name": "Rotary Kiln 3 (72m x 4.6m)",
                "type": "RotaryKiln",
                "position": {"x": 880, "y": 480},
                "parameters": {"length_m": 72.0, "diameter_m": 4.6, "slope_pct": 3.5, "speed_rpm": 3.79, "target_burning_zone_c": 1435.0},
            },
            {
                "id": "FUEL_KILN",
                "name": "Kiln Main Burner Fuel",
                "type": "FuelFeeder",
                "position": {"x": 1080, "y": 620},
                "parameters": {"fuel_name": "Petcoke Main", "nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            },
            {
                "id": "COOLER_01",
                "name": "Hydraulic Grate Cooler",
                "type": "GrateCooler",
                "position": {"x": 1080, "y": 440},
                "parameters": {"grate_area_m2": 105.0, "cooling_air_total_tph": 348.5, "recuperation_efficiency": 0.74},
            },
            {
                "id": "ID_FAN_01",
                "name": "Main ID Process Fan",
                "type": "IDFan",
                "position": {"x": 80, "y": 200},
                "parameters": {"design_flow_nm3h": 350000.0, "damper_pct": 82.0, "motor_rated_kw": 2500.0},
            },
            {
                "id": "SILO_CLINKER",
                "name": "Clinker Storage Dome",
                "type": "SiloStorage",
                "position": {"x": 1260, "y": 440},
                "parameters": {"capacity_tons": 50000.0, "initial_level_pct": 45.0},
            },
        ],
        "connections": [
            {"stream_id": 1, "name": "Raw Meal Total Feed", "source": {"block": "FEED_01", "port": "out_solid"}, "target": {"block": "CYC_01", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 2, "name": "Stage 1 Meal to Stage 2", "source": {"block": "CYC_01", "port": "out_meal"}, "target": {"block": "CYC_02", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 3, "name": "Stage 2 Meal to Stage 3", "source": {"block": "CYC_02", "port": "out_meal"}, "target": {"block": "CYC_03", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 4, "name": "Stage 3 Meal to Stage 4", "source": {"block": "CYC_03", "port": "out_meal"}, "target": {"block": "CYC_04", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 5, "name": "Stage 4 Meal to Calciner", "source": {"block": "CYC_04", "port": "out_meal"}, "target": {"block": "CALC_01", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 6, "name": "Precalciner Fuel Supply", "source": {"block": "FUEL_PC", "port": "out_fuel"}, "target": {"block": "CALC_01", "port": "in_fuel"}, "phase": "FUEL"},
            {"stream_id": 7, "name": "Tertiary Air Duct", "source": {"block": "COOLER_01", "port": "out_tertiary_air"}, "target": {"block": "CALC_01", "port": "in_tertiary_air"}, "phase": "AIR"},
            {"stream_id": 8, "name": "Kiln Inlet Exhaust Gas", "source": {"block": "KILN_01", "port": "out_kiln_gas"}, "target": {"block": "CALC_01", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 9, "name": "Calciner Flue Gas to Stage 5", "source": {"block": "CALC_01", "port": "out_gas"}, "target": {"block": "CYC_05", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 10, "name": "Calciner Decarbonated Meal to Stage 5", "source": {"block": "CALC_01", "port": "out_meal"}, "target": {"block": "CYC_05", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 11, "name": "Stage 5 Flue Gas to Stage 4", "source": {"block": "CYC_05", "port": "out_gas"}, "target": {"block": "CYC_04", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 12, "name": "Stage 4 Flue Gas to Stage 3", "source": {"block": "CYC_04", "port": "out_gas"}, "target": {"block": "CYC_03", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 13, "name": "Stage 3 Flue Gas to Stage 2", "source": {"block": "CYC_03", "port": "out_gas"}, "target": {"block": "CYC_02", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 14, "name": "Stage 2 Flue Gas to Stage 1", "source": {"block": "CYC_02", "port": "out_gas"}, "target": {"block": "CYC_01", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 15, "name": "Preheater Top Gas to ID Fan", "source": {"block": "CYC_01", "port": "out_gas"}, "target": {"block": "ID_FAN_01", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 16, "name": "Decarbonated Meal to Kiln", "source": {"block": "CYC_05", "port": "out_meal"}, "target": {"block": "KILN_01", "port": "in_meal_calcined"}, "phase": "SOLID"},
            {"stream_id": 17, "name": "Kiln Main Burner Flame Fuel", "source": {"block": "FUEL_KILN", "port": "out_fuel"}, "target": {"block": "KILN_01", "port": "in_flame_fuel"}, "phase": "FUEL"},
            {"stream_id": 18, "name": "Hot Secondary Air to Kiln", "source": {"block": "COOLER_01", "port": "out_secondary_air"}, "target": {"block": "KILN_01", "port": "in_secondary_air"}, "phase": "AIR"},
            {"stream_id": 19, "name": "Hot Clinker to Grate Cooler", "source": {"block": "KILN_01", "port": "out_clinker"}, "target": {"block": "COOLER_01", "port": "in_clinker_hot"}, "phase": "SOLID"},
            {"stream_id": 20, "name": "Cooled Clinker to Dome Silo", "source": {"block": "COOLER_01", "port": "out_clinker_cool"}, "target": {"block": "SILO_CLINKER", "port": "in_solid"}, "phase": "SOLID"},
        ],
    }


def build_single_cyclone_demo_template() -> Dict[str, Any]:
    """Generates a minimal single-cyclone test loop."""
    return {
        "flowsheet_id": "single_cyclone_demo",
        "name": "Single Cyclone Preheater Test Loop",
        "version": "2.0",
        "description": "Minimal flowsheet demonstrating gas-solid counter-current thermal exchange.",
        "components": [
            {
                "id": "FEED_01",
                "name": "Raw Meal Feeder",
                "type": "GravimetricFeeder",
                "position": {"x": 100, "y": 100},
                "parameters": {"nominal_rate_tph": 150.0, "temperature_c": 50.0},
            },
            {
                "id": "CYC_01",
                "name": "Cyclone Stage 1",
                "type": "CycloneStage",
                "position": {"x": 360, "y": 150},
                "parameters": {"stage_number": 1, "separation_efficiency": 0.95, "thermal_effectiveness": 0.82, "dp_mbar": 5.0},
            },
            {
                "id": "DAMPER_01",
                "name": "Hot Gas Riser Damper",
                "type": "DamperValve",
                "position": {"x": 360, "y": 380},
                "parameters": {"opening_pct": 85.0},
            },
            {
                "id": "SILO_01",
                "name": "Collected Meal Bin",
                "type": "SiloStorage",
                "position": {"x": 620, "y": 280},
                "parameters": {"capacity_tons": 500.0},
            },
            {
                "id": "FAN_01",
                "name": "Suction Draft Fan",
                "type": "IDFan",
                "position": {"x": 620, "y": 100},
                "parameters": {"design_flow_nm3h": 120000.0, "damper_pct": 75.0},
            },
        ],
        "connections": [
            {"stream_id": 1, "name": "Raw Meal Inflow", "source": {"block": "FEED_01", "port": "out_solid"}, "target": {"block": "CYC_01", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 2, "name": "Hot Flue Gas Entry", "source": {"block": "DAMPER_01", "port": "out_stream"}, "target": {"block": "CYC_01", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 3, "name": "Captured Meal Discharge", "source": {"block": "CYC_01", "port": "out_meal"}, "target": {"block": "SILO_01", "port": "in_solid"}, "phase": "SOLID"},
            {"stream_id": 4, "name": "Cooled Gas Exhaust", "source": {"block": "CYC_01", "port": "out_gas"}, "target": {"block": "FAN_01", "port": "in_gas"}, "phase": "GAS"},
        ],
    }


def build_calciner_combustion_loop_template() -> Dict[str, Any]:
    """Generates precalciner combustion loop template."""
    return {
        "flowsheet_id": "calciner_combustion_loop",
        "name": "Precalciner Combustion & Decarbonation Loop",
        "version": "2.0",
        "description": "Arrhenius decarbonation kinetics, multi-fuel combustion, and bottom separation stage.",
        "components": [
            {
                "id": "FEED_MEAL",
                "name": "Preheated Meal Feed",
                "type": "GravimetricFeeder",
                "position": {"x": 100, "y": 100},
                "parameters": {"nominal_rate_tph": 280.0, "temperature_c": 760.0},
            },
            {
                "id": "FEED_FUEL",
                "name": "Petcoke Feeder",
                "type": "FuelFeeder",
                "position": {"x": 100, "y": 240},
                "parameters": {"nominal_rate_tph": 11.5, "lhv_mj_kg": 31.4},
            },
            {
                "id": "VALVE_TA",
                "name": "Tertiary Air Damper",
                "type": "DamperValve",
                "position": {"x": 100, "y": 380},
                "parameters": {"opening_pct": 90.0},
            },
            {
                "id": "CALCINER",
                "name": "Precalciner Chamber",
                "type": "CalcinerReactor",
                "position": {"x": 380, "y": 240},
                "parameters": {"volume_m3": 1100.0, "design_calcination_pct": 93.0},
            },
            {
                "id": "CYCLONE_5",
                "name": "Bottom Separator Cyclone",
                "type": "CycloneStage",
                "position": {"x": 640, "y": 200},
                "parameters": {"stage_number": 5, "separation_efficiency": 0.95},
            },
            {
                "id": "FAN_EXHAUST",
                "name": "Exhaust Gas Fan",
                "type": "IDFan",
                "position": {"x": 880, "y": 140},
                "parameters": {"damper_pct": 85.0},
            },
            {
                "id": "KILN_FEED_BIN",
                "name": "Decarbonated Meal Bin",
                "type": "SiloStorage",
                "position": {"x": 880, "y": 320},
                "parameters": {"capacity_tons": 2000.0},
            },
        ],
        "connections": [
            {"stream_id": 1, "name": "Raw Meal to Calciner", "source": {"block": "FEED_MEAL", "port": "out_solid"}, "target": {"block": "CALCINER", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 2, "name": "Petcoke to Burners", "source": {"block": "FEED_FUEL", "port": "out_fuel"}, "target": {"block": "CALCINER", "port": "in_fuel"}, "phase": "FUEL"},
            {"stream_id": 3, "name": "Tertiary Air to Calciner", "source": {"block": "VALVE_TA", "port": "out_stream"}, "target": {"block": "CALCINER", "port": "in_tertiary_air"}, "phase": "AIR"},
            {"stream_id": 4, "name": "Calciner Suspension Mix", "source": {"block": "CALCINER", "port": "out_gas_meal_mix"}, "target": {"block": "CYCLONE_5", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 5, "name": "Separated Hot Gas", "source": {"block": "CYCLONE_5", "port": "out_gas"}, "target": {"block": "FAN_EXHAUST", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 6, "name": "Decarbonated Meal Discharge", "source": {"block": "CYCLONE_5", "port": "out_meal"}, "target": {"block": "KILN_FEED_BIN", "port": "in_solid"}, "phase": "SOLID"},
        ],
    }


def build_lime_kiln_template() -> Dict[str, Any]:
    """Generates rotary lime kiln flowsheet template."""
    return {
        "flowsheet_id": "lime_kiln_calciner",
        "name": "Rotary Lime Kiln Quicklime Production",
        "version": "2.0",
        "description": "High-calcium limestone calcination to quicklime (CaO) with cooler heat recuperation.",
        "components": [
            {
                "id": "FEED_STONE",
                "name": "Limestone Stone Feeder",
                "type": "GravimetricFeeder",
                "position": {"x": 100, "y": 120},
                "parameters": {
                    "nominal_rate_tph": 180.0,
                    "temperature_c": 20.0,
                    "caco3_pct": 94.5,
                    "mgco3_pct": 1.8,
                    "sio2_pct": 2.2,
                    "al2o3_pct": 0.6,
                    "fe2o3_pct": 0.4,
                    "moisture_pct": 1.2,
                },
            },
            {
                "id": "LIME_KILN",
                "name": "Rotary Lime Kiln (55m x 3.8m)",
                "type": "RotaryKiln",
                "position": {"x": 380, "y": 200},
                "parameters": {"length_m": 55.0, "diameter_m": 3.8, "speed_rpm": 2.2, "target_burning_zone_c": 1280.0},
            },
            {
                "id": "GAS_BURNER",
                "name": "Kiln Gas Burner",
                "type": "FuelFeeder",
                "position": {"x": 380, "y": 380},
                "parameters": {"fuel_name": "Natural Gas", "nominal_rate_tph": 6.8, "lhv_mj_kg": 46.5},
            },
            {
                "id": "LIME_COOLER",
                "name": "Lime Satellite/Grate Cooler",
                "type": "GrateCooler",
                "position": {"x": 660, "y": 240},
                "parameters": {"grate_area_m2": 65.0, "cooling_air_total_tph": 180.0, "secondary_air_split_pct": 55.0, "tertiary_air_split_pct": 0.0},
            },
            {
                "id": "LIME_SILO",
                "name": "Quicklime (CaO) Product Silo",
                "type": "SiloStorage",
                "position": {"x": 920, "y": 240},
                "parameters": {"capacity_tons": 15000.0},
            },
            {
                "id": "KILN_FAN",
                "name": "Kiln Exhaust ID Fan",
                "type": "IDFan",
                "position": {"x": 380, "y": 40},
                "parameters": {"design_flow_nm3h": 160000.0, "damper_pct": 78.0},
            },
        ],
        "connections": [
            {"stream_id": 1, "name": "Limestone Bed Feed", "source": {"block": "FEED_STONE", "port": "out_solid"}, "target": {"block": "LIME_KILN", "port": "in_meal_calcined"}, "phase": "SOLID"},
            {"stream_id": 2, "name": "Combustion Gas Fuel", "source": {"block": "GAS_BURNER", "port": "out_fuel"}, "target": {"block": "LIME_KILN", "port": "in_flame_fuel"}, "phase": "FUEL"},
            {"stream_id": 3, "name": "Secondary Preheated Air", "source": {"block": "LIME_COOLER", "port": "out_secondary_air"}, "target": {"block": "LIME_KILN", "port": "in_secondary_air"}, "phase": "AIR"},
            {"stream_id": 4, "name": "Hot Quicklime Discharge", "source": {"block": "LIME_KILN", "port": "out_clinker"}, "target": {"block": "LIME_COOLER", "port": "in_clinker_hot"}, "phase": "SOLID"},
            {"stream_id": 5, "name": "Cooled Quicklime to Storage", "source": {"block": "LIME_COOLER", "port": "out_clinker_cool"}, "target": {"block": "LIME_SILO", "port": "in_solid"}, "phase": "SOLID"},
            {"stream_id": 6, "name": "Kiln Flue Gas to ID Fan", "source": {"block": "LIME_KILN", "port": "out_kiln_gas"}, "target": {"block": "KILN_FAN", "port": "in_gas"}, "phase": "GAS"},
        ],
    }


def build_dual_fuel_rdf_template() -> Dict[str, Any]:
    """Generates precalciner flowsheet co-firing coal and RDF through a FuelMixer sum node."""
    return {
        "flowsheet_id": "dual_fuel_calciner_rdf",
        "name": "Calciner Multi-Fuel Co-Firing (Coal + RDF Sum Node)",
        "version": "2.0",
        "description": "Precalciner co-firing primary coal and Refuse-Derived Fuel (RDF) blended via FuelMixer sum node with online TSR% tracking.",
        "components": [
            {
                "id": "FEED_MEAL",
                "name": "Preheated Meal Feed",
                "type": "GravimetricFeeder",
                "position": {"x": 80, "y": 80},
                "parameters": {"nominal_rate_tph": 280.0, "temperature_c": 760.0},
            },
            {
                "id": "FUEL_COAL",
                "name": "Primary Pulverized Coal",
                "type": "FuelFeeder",
                "position": {"x": 80, "y": 200},
                "parameters": {"fuel_name": "Bituminous Coal", "nominal_rate_tph": 8.0, "lhv_mj_kg": 29.5, "ash_pct": 10.0, "moisture_pct": 2.0},
            },
            {
                "id": "FUEL_RDF",
                "name": "Refuse-Derived Fuel (RDF)",
                "type": "FuelFeeder",
                "position": {"x": 80, "y": 340},
                "parameters": {"fuel_name": "Fluff RDF Alt Fuel", "nominal_rate_tph": 4.5, "lhv_mj_kg": 18.5, "ash_pct": 14.5, "moisture_pct": 16.0},
            },
            {
                "id": "SUM_FUEL",
                "name": "Fuel Blend Sum Node",
                "type": "FuelMixer",
                "position": {"x": 320, "y": 270},
                "parameters": {},
            },
            {
                "id": "VALVE_TA",
                "name": "Tertiary Air Damper",
                "type": "DamperValve",
                "position": {"x": 320, "y": 430},
                "parameters": {"opening_pct": 92.0},
            },
            {
                "id": "CALCINER",
                "name": "Precalciner Chamber",
                "type": "CalcinerReactor",
                "position": {"x": 560, "y": 240},
                "parameters": {"volume_m3": 1100.0, "design_calcination_pct": 93.0},
            },
            {
                "id": "CYCLONE_5",
                "name": "Bottom Separator Cyclone",
                "type": "CycloneStage",
                "position": {"x": 820, "y": 200},
                "parameters": {"stage_number": 5, "separation_efficiency": 0.95},
            },
            {
                "id": "FAN_EXHAUST",
                "name": "Exhaust Gas Fan",
                "type": "IDFan",
                "position": {"x": 1060, "y": 140},
                "parameters": {"damper_pct": 85.0},
            },
            {
                "id": "KILN_FEED_BIN",
                "name": "Decarbonated Meal Bin",
                "type": "SiloStorage",
                "position": {"x": 1060, "y": 320},
                "parameters": {"capacity_tons": 2000.0},
            },
        ],
        "connections": [
            {"stream_id": 1, "name": "Raw Meal to Calciner", "source": {"block": "FEED_MEAL", "port": "out_solid"}, "target": {"block": "CALCINER", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 2, "name": "Primary Coal to Mixer", "source": {"block": "FUEL_COAL", "port": "out_fuel"}, "target": {"block": "SUM_FUEL", "port": "in_fuel_1"}, "phase": "FUEL"},
            {"stream_id": 3, "name": "RDF Alt Fuel to Mixer", "source": {"block": "FUEL_RDF", "port": "out_fuel"}, "target": {"block": "SUM_FUEL", "port": "in_fuel_2"}, "phase": "FUEL"},
            {"stream_id": 4, "name": "Blended Fuel to Burners", "source": {"block": "SUM_FUEL", "port": "out_fuel"}, "target": {"block": "CALCINER", "port": "in_fuel"}, "phase": "FUEL"},
            {"stream_id": 5, "name": "Tertiary Air to Calciner", "source": {"block": "VALVE_TA", "port": "out_stream"}, "target": {"block": "CALCINER", "port": "in_tertiary_air"}, "phase": "AIR"},
            {"stream_id": 6, "name": "Calciner Suspension Mix", "source": {"block": "CALCINER", "port": "out_gas_meal_mix"}, "target": {"block": "CYCLONE_5", "port": "in_meal"}, "phase": "SOLID"},
            {"stream_id": 7, "name": "Separated Hot Gas", "source": {"block": "CYCLONE_5", "port": "out_gas"}, "target": {"block": "FAN_EXHAUST", "port": "in_gas"}, "phase": "GAS"},
            {"stream_id": 8, "name": "Decarbonated Meal Discharge", "source": {"block": "CYCLONE_5", "port": "out_meal"}, "target": {"block": "KILN_FEED_BIN", "port": "in_solid"}, "phase": "SOLID"},
        ],
    }


TEMPLATE_BUILDERS = {
    "kiln_3_pyroprocess": build_kiln3_pyroprocess_template,
    "single_cyclone_demo": build_single_cyclone_demo_template,
    "calciner_combustion_loop": build_calciner_combustion_loop_template,
    "dual_fuel_calciner_rdf": build_dual_fuel_rdf_template,
    "lime_kiln_calciner": build_lime_kiln_template,
}


def load_template_graph(template_id: str) -> FlowsheetGraph:
    """Instantiates a FlowsheetGraph from a pre-built template ID."""
    if template_id not in TEMPLATE_BUILDERS:
        raise KeyError(f"Unknown template ID: '{template_id}'")
    data = TEMPLATE_BUILDERS[template_id]()
    return FlowsheetGraph.from_dict(data, block_factory=get_block_class)

