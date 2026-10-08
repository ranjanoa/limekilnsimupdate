"""
Operational Scenarios Engine for Cement & Lime Pyroprocessing Plants.
Provides canonical industrial operating modes, production turndown/surge,
thermal disturbances, trip events, alternative fuel firing, and aerodynamic imbalances
with automated validation against first-principles physics.
"""

from typing import Dict, Any, List, Optional
import copy
import logging

from .flowsheet_graph import FlowsheetGraph
from .solver import FlowsheetSolver

logger = logging.getLogger("OperationalScenarios")

OPERATIONAL_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "nominal_baseline",
        "name": "Nominal Design Baseline (280 t/h)",
        "category": "Baseline Operations",
        "severity": "NORMAL",
        "icon": "⚖️",
        "description": "Plant operating at nominal 280.0 t/h raw meal feed, 7.2 t/h kiln fuel, and 12.0 t/h calciner fuel. Produces ~175 t/h clinker at 1414°C BZT, 866°C calciner temperature, and 91.0% decarbonation.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
            "ID_FAN_01": {"damper_pct": 82.0},
            "COOLER_01": {"cooling_air_total_tph": 348.5, "clinker_target_temp_c": 95.0},
        },
        "expected_checks": {
            "calciner_temp_range": [850.0, 880.0],
            "bzt_range": [1400.0, 1440.0],
            "calcination_range": [89.0, 93.0],
            "free_lime_range": [1.2, 2.2],
            "clinker_rate_min": 170.0,
        },
    },
    {
        "id": "turndown_unbalanced",
        "name": "Sudden Feed Drop / Unbalanced (200 t/h)",
        "category": "Production Load",
        "severity": "WARNING",
        "icon": "📉",
        "description": "Feed abruptly cuts from 280 to 200 t/h (-28.5%) without trimming fuels. Reduced endothermic calcination load causes calciner temperature to spike to ~988°C and decarbonation to reach 98.5%.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 200.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
        },
        "expected_checks": {
            "calciner_temp_min": 950.0,
            "calcination_min": 97.0,
            "bzt_min": 1420.0,
            "clinker_rate_max": 130.0,
        },
    },
    {
        "id": "turndown_balanced",
        "name": "Optimized Turndown (200 t/h Balanced)",
        "category": "Production Load",
        "severity": "OPTIMIZED",
        "icon": "✨",
        "description": "Controlled turndown to 200 t/h with fuel rates trimmed (Kiln: 7.0 t/h, PC: 10.0 t/h), sustaining optimal 878°C precalciner temperature and 91.9% decarbonation while absorbing constant shell heat losses.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 200.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.0, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 10.3, "lhv_mj_kg": 27.5},
            "ID_FAN_01": {"damper_pct": 74.0},
            "COOLER_01": {"cooling_air_total_tph": 260.0},
        },
        "expected_checks": {
            "calciner_temp_range": [840.0, 915.0],
            "bzt_range": [1380.0, 1435.0],
            "calcination_range": [88.0, 95.0],
            "clinker_rate_max": 135.0,
        },
    },
    {
        "id": "surge_overload",
        "name": "Maximum Feed Surge / Overload (315 t/h)",
        "category": "Production Load",
        "severity": "WARNING",
        "icon": "📈",
        "description": "Feed pushed to maximum capacity of 315 t/h (+12.5%) without fuel compensation. The high meal thermal burden suppresses calciner temperature below 820°C and drops decarbonation to ~86.8%.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 315.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
        },
        "expected_checks": {
            "calciner_temp_max": 830.0,
            "calcination_max": 88.0,
            "clinker_rate_min": 190.0,
        },
    },
    {
        "id": "surge_compensated",
        "name": "High Capacity Compensated (315 t/h Tuned)",
        "category": "Production Load",
        "severity": "OPTIMIZED",
        "icon": "🚀",
        "description": "Feed pushed to 315 t/h with compensatory fuel boost (Kiln: 7.3 t/h, PC: 13.0 t/h) and ID fan damper open to 90%, sustaining 196.8 t/h clinker output with complete calcination.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 315.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.3, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 13.0, "lhv_mj_kg": 27.5},
            "ID_FAN_01": {"damper_pct": 90.0},
            "COOLER_01": {"cooling_air_total_tph": 390.0},
        },
        "expected_checks": {
            "calciner_temp_range": [850.0, 890.0],
            "bzt_range": [1400.0, 1445.0],
            "calcination_range": [89.0, 94.0],
            "clinker_rate_min": 190.0,
        },
    },
    {
        "id": "kiln_overheating",
        "name": "Main Burner Over-Firing (Overheating)",
        "category": "Thermal & Combustion",
        "severity": "CRITICAL",
        "icon": "🔥",
        "description": "Excess fuel firing at main burner (8.8 t/h, +22%). Burning zone temperature exceeds 1500°C, Free Lime drops below 0.5% (overburned hard clinker), and kiln inlet gas rises above 1100°C.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 8.8, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
        },
        "expected_checks": {
            "bzt_min": 1490.0,
            "free_lime_max": 0.8,
            "kiln_inlet_gas_min": 1080.0,
        },
    },
    {
        "id": "kiln_underburning",
        "name": "Main Burner Fuel Starvation / Trip",
        "category": "Thermal & Combustion",
        "severity": "CRITICAL",
        "icon": "❄️",
        "description": "Main burner fuel rate drops to 5.0 t/h (-30%). Burning zone temperature collapses to ~1150°C and Free Lime surges exponentially to 6.0%, creating an immediate underburning quality trip.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 5.0, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
        },
        "expected_checks": {
            "bzt_max": 1250.0,
            "free_lime_min": 4.5,
            "kiln_inlet_gas_max": 990.0,
        },
    },
    {
        "id": "pc_fuel_trip",
        "name": "Precalciner Fuel Partial Trip (-40%)",
        "category": "Disturbances & Trips",
        "severity": "CRITICAL",
        "icon": "⚠️",
        "description": "Precalciner coal dosing feeder fault cuts fuel from 12.0 to 7.2 t/h. Calciner temperature plummets below 750°C, decarbonation collapses to ~79%, discharging raw uncalcined meal into the kiln.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 27.5},
        },
        "expected_checks": {
            "calciner_temp_max": 760.0,
            "calcination_max": 82.0,
        },
    },
    {
        "id": "alternative_fuel_surge",
        "name": "High RDF / Alternative Fuel Substitution",
        "category": "Alternative Energy",
        "severity": "NORMAL",
        "icon": "♻️",
        "description": "Precalciner firing shifted to Refuse-Derived Fuel (RDF) with lower calorific value (20.0 MJ/kg vs 27.5 MJ/kg) at higher mass dosing (16.5 t/h). Flue gas volume expands while decarbonation remains stable.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 16.5, "lhv_mj_kg": 20.0},
            "ID_FAN_01": {"damper_pct": 86.0},
        },
        "expected_checks": {
            "calciner_temp_range": [840.0, 890.0],
            "calcination_range": [88.0, 93.0],
        },
    },
    {
        "id": "cooler_fan_trip",
        "name": "Grate Cooler Cooling Fan Trip / Under-Aeration",
        "category": "Cooler & Aeration",
        "severity": "WARNING",
        "icon": "💨",
        "description": "Cooler fan aeration throttled from 348.5 to 180.0 t/h. Reduced cooling air causes clinker discharge temperature to surge above 160°C and reduces heat recuperation to the kiln.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
            "COOLER_01": {"cooling_air_total_tph": 180.0},
        },
        "expected_checks": {
            "clinker_exit_temp_min": 140.0,
        },
    },
    {
        "id": "id_draft_starvation",
        "name": "ID Fan Draft Restriction / Flue Backpressure",
        "category": "Aerodynamics & Draft",
        "severity": "WARNING",
        "icon": "🌪️",
        "description": "ID fan damper throttled from 82% to 55%. System differential pressure drops from ~58 mbar to ~28 mbar, causing draft starvation in the preheater tower.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
            "ID_FAN_01": {"damper_pct": 55.0},
        },
        "expected_checks": {
            "fan_dp_max": 35.0,
        },
    },
    {
        "id": "id_draft_surge",
        "name": "High ID Fan Draft / Max Suction (98%)",
        "category": "Aerodynamics & Draft",
        "severity": "NORMAL",
        "icon": "⚡",
        "description": "Inlet damper opened fully to 98%. Differential pressure reaches ~62 mbar and motor power demand surges above 2,000 kW.",
        "overrides": {
            "FEED_01": {"nominal_rate_tph": 280.0},
            "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
            "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
            "ID_FAN_01": {"damper_pct": 98.0},
        },
        "expected_checks": {
            "fan_dp_min": 58.0,
            "fan_power_min": 1100.0,
        },
    },
]


def get_scenarios_catalog() -> List[Dict[str, Any]]:
    """Returns the complete manifest of operational scenarios."""
    return copy.deepcopy(OPERATIONAL_SCENARIOS)


def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Looks up a scenario by ID."""
    for scn in OPERATIONAL_SCENARIOS:
        if scn["id"] == scenario_id:
            return copy.deepcopy(scn)
    return None


BASELINE_PARAMETERS = {
    "FEED_01": {"nominal_rate_tph": 280.0},
    "FUEL_KILN": {"nominal_rate_tph": 7.2, "lhv_mj_kg": 31.4},
    "FUEL_PC": {"nominal_rate_tph": 12.0, "lhv_mj_kg": 27.5},
    "ID_FAN_01": {"damper_pct": 82.0, "design_dp_mbar": 65.0},
    "COOLER_01": {"cooling_air_total_tph": 348.5, "clinker_target_temp_c": 95.0},
}


def apply_scenario(manager: Any, scenario_id: str) -> Dict[str, Any]:
    """
    Applies an operational scenario by ID to the active flowsheet in ModularEngineManager,
    re-solves closed-loop steady-state balances, checks verification rules,
    and returns full diagnostic telemetry.
    """
    scn = get_scenario_by_id(scenario_id)
    if not scn:
        return {"status": "error", "message": f"Scenario '{scenario_id}' not found."}

    # Reset standard baseline parameters first for deterministic repeatability
    for b_id, b_params in BASELINE_PARAMETERS.items():
        if b_id in manager.active_graph.blocks:
            for p_name, p_val in b_params.items():
                manager.update_block_parameter(b_id, p_name, p_val)

    overrides = scn.get("overrides", {})
    # Apply parameter overrides
    for block_id, params in overrides.items():
        if block_id in manager.active_graph.blocks:
            for param_name, val in params.items():
                manager.update_block_parameter(block_id, param_name, val)

    # Re-solve steady state
    solve_res = manager.solver.solve_steady_state()
    audit = manager.active_graph.audit_plant_conservation()
    telemetry = manager.solver.get_blocks_telemetry()
    stream_table = manager.solver.get_stream_table()

    # Validate against expected checks
    validation = validate_scenario_results(scn, telemetry)

    return {
        "status": "success",
        "scenario": {
            "id": scn["id"],
            "name": scn["name"],
            "category": scn["category"],
            "severity": scn["severity"],
            "icon": scn["icon"],
            "description": scn["description"],
        },
        "solve_result": solve_res,
        "validation": validation,
        "audit": audit,
        "telemetry": telemetry,
        "stream_table": stream_table,
    }


def validate_scenario_results(scenario: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Validates simulation state against expected physical bounds for the scenario."""
    checks = scenario.get("expected_checks", {})
    results: List[Dict[str, Any]] = []
    all_passed = True

    calc_state = telemetry.get("CALC_01", {}).get("state", {})
    kiln_state = telemetry.get("KILN_01", {}).get("state", {})
    cooler_state = telemetry.get("COOLER_01", {}).get("state", {})
    fan_state = telemetry.get("ID_FAN_01", {}).get("state", {})

    t_calc = calc_state.get("calciner_temp_c", 0.0)
    decarb = calc_state.get("calcination_degree_pct", 0.0)
    bzt = kiln_state.get("burning_zone_temp_c", 0.0)
    free_lime = kiln_state.get("free_lime_pct", 0.0)
    clinker_rate = kiln_state.get("clinker_rate_tph", 0.0)
    kiln_inlet_gas = kiln_state.get("kiln_inlet_gas_temp_c", 0.0)
    clinker_exit_t = cooler_state.get("clinker_exit_temp_c", 0.0)
    fan_dp = fan_state.get("fan_dp_mbar", 0.0)
    fan_power = fan_state.get("motor_power_kw", 0.0)

    # 1. Calciner Temp Checks
    if "calciner_temp_range" in checks:
        lo, hi = checks["calciner_temp_range"]
        passed = lo <= t_calc <= hi
        all_passed = all_passed and passed
        results.append({"metric": "Calciner Temp (°C)", "actual": t_calc, "expected": f"{lo} - {hi}", "passed": passed})
    if "calciner_temp_min" in checks:
        val = checks["calciner_temp_min"]
        passed = t_calc >= val
        all_passed = all_passed and passed
        results.append({"metric": "Calciner Temp Min (°C)", "actual": t_calc, "expected": f">= {val}", "passed": passed})
    if "calciner_temp_max" in checks:
        val = checks["calciner_temp_max"]
        passed = t_calc <= val
        all_passed = all_passed and passed
        results.append({"metric": "Calciner Temp Max (°C)", "actual": t_calc, "expected": f"<= {val}", "passed": passed})

    # 2. Calcination Checks
    if "calcination_range" in checks:
        lo, hi = checks["calcination_range"]
        passed = lo <= decarb <= hi
        all_passed = all_passed and passed
        results.append({"metric": "Decarbonation (%)", "actual": decarb, "expected": f"{lo} - {hi}", "passed": passed})
    if "calcination_min" in checks:
        val = checks["calcination_min"]
        passed = decarb >= val
        all_passed = all_passed and passed
        results.append({"metric": "Decarbonation Min (%)", "actual": decarb, "expected": f">= {val}", "passed": passed})
    if "calcination_max" in checks:
        val = checks["calcination_max"]
        passed = decarb <= val
        all_passed = all_passed and passed
        results.append({"metric": "Decarbonation Max (%)", "actual": decarb, "expected": f"<= {val}", "passed": passed})

    # 3. BZT Checks
    if "bzt_range" in checks:
        lo, hi = checks["bzt_range"]
        passed = lo <= bzt <= hi
        all_passed = all_passed and passed
        results.append({"metric": "BZT (°C)", "actual": bzt, "expected": f"{lo} - {hi}", "passed": passed})
    if "bzt_min" in checks:
        val = checks["bzt_min"]
        passed = bzt >= val
        all_passed = all_passed and passed
        results.append({"metric": "BZT Min (°C)", "actual": bzt, "expected": f">= {val}", "passed": passed})
    if "bzt_max" in checks:
        val = checks["bzt_max"]
        passed = bzt <= val
        all_passed = all_passed and passed
        results.append({"metric": "BZT Max (°C)", "actual": bzt, "expected": f"<= {val}", "passed": passed})

    # 4. Free Lime Checks
    if "free_lime_range" in checks:
        lo, hi = checks["free_lime_range"]
        passed = lo <= free_lime <= hi
        all_passed = all_passed and passed
        results.append({"metric": "Free Lime (%)", "actual": free_lime, "expected": f"{lo} - {hi}", "passed": passed})
    if "free_lime_min" in checks:
        val = checks["free_lime_min"]
        passed = free_lime >= val
        all_passed = all_passed and passed
        results.append({"metric": "Free Lime Min (%)", "actual": free_lime, "expected": f">= {val}", "passed": passed})
    if "free_lime_max" in checks:
        val = checks["free_lime_max"]
        passed = free_lime <= val
        all_passed = all_passed and passed
        results.append({"metric": "Free Lime Max (%)", "actual": free_lime, "expected": f"<= {val}", "passed": passed})

    # 5. Clinker Rate Checks
    if "clinker_rate_min" in checks:
        val = checks["clinker_rate_min"]
        passed = clinker_rate >= val
        all_passed = all_passed and passed
        results.append({"metric": "Clinker Rate Min (t/h)", "actual": clinker_rate, "expected": f">= {val}", "passed": passed})
    if "clinker_rate_max" in checks:
        val = checks["clinker_rate_max"]
        passed = clinker_rate <= val
        all_passed = all_passed and passed
        results.append({"metric": "Clinker Rate Max (t/h)", "actual": clinker_rate, "expected": f"<= {val}", "passed": passed})

    # 6. Kiln Inlet Gas Checks
    if "kiln_inlet_gas_min" in checks:
        val = checks["kiln_inlet_gas_min"]
        passed = kiln_inlet_gas >= val
        all_passed = all_passed and passed
        results.append({"metric": "Kiln Inlet Gas Min (°C)", "actual": kiln_inlet_gas, "expected": f">= {val}", "passed": passed})
    if "kiln_inlet_gas_max" in checks:
        val = checks["kiln_inlet_gas_max"]
        passed = kiln_inlet_gas <= val
        all_passed = all_passed and passed
        results.append({"metric": "Kiln Inlet Gas Max (°C)", "actual": kiln_inlet_gas, "expected": f"<= {val}", "passed": passed})

    # 7. Clinker Exit Temp Checks
    if "clinker_exit_temp_min" in checks:
        val = checks["clinker_exit_temp_min"]
        passed = clinker_exit_t >= val
        all_passed = all_passed and passed
        results.append({"metric": "Clinker Exit Temp Min (°C)", "actual": clinker_exit_t, "expected": f">= {val}", "passed": passed})

    # 8. Fan Checks
    if "fan_dp_min" in checks:
        val = checks["fan_dp_min"]
        passed = fan_dp >= val
        all_passed = all_passed and passed
        results.append({"metric": "Fan DP Min (mbar)", "actual": fan_dp, "expected": f">= {val}", "passed": passed})
    if "fan_dp_max" in checks:
        val = checks["fan_dp_max"]
        passed = fan_dp <= val
        all_passed = all_passed and passed
        results.append({"metric": "Fan DP Max (mbar)", "actual": fan_dp, "expected": f"<= {val}", "passed": passed})
    if "fan_power_min" in checks:
        val = checks["fan_power_min"]
        passed = fan_power >= val
        all_passed = all_passed and passed
        results.append({"metric": "Fan Power Min (kW)", "actual": fan_power, "expected": f">= {val}", "passed": passed})

    return {
        "all_passed": all_passed,
        "checks_count": len(results),
        "details": results,
    }


def verify_all_scenarios(manager: Any) -> Dict[str, Any]:
    """
    Executes automated test verification across ALL scenarios sequentially.
    Ensures that steady-state convergence, physical plausibility, mass/energy conservation,
    and reaction kinetics work reliably across all operating envelopes.
    """
    summary = []
    total_passed = 0

    for scn in OPERATIONAL_SCENARIOS:
        scn_id = scn["id"]
        res = apply_scenario(manager, scn_id)
        if res["status"] != "success":
            summary.append({
                "id": scn_id,
                "name": scn["name"],
                "passed": False,
                "converged": False,
                "error": res.get("message", "Unknown error"),
            })
            continue

        converged = res["solve_result"].get("converged", False)
        closure_pct = res["audit"].get("mass_closure_pct", 0.0)
        validation = res.get("validation", {})
        val_passed = validation.get("all_passed", False)
        passed = converged and val_passed and (closure_pct >= 95.0)

        if passed:
            total_passed += 1

        summary.append({
            "id": scn_id,
            "name": scn["name"],
            "category": scn["category"],
            "severity": scn["severity"],
            "passed": passed,
            "converged": converged,
            "mass_closure_pct": closure_pct,
            "iterations": res["solve_result"].get("iterations", 0),
            "validation_details": validation.get("details", []),
            "telemetry_sample": {
                "calciner_temp_c": res["telemetry"].get("CALC_01", {}).get("state", {}).get("calciner_temp_c"),
                "decarb_pct": res["telemetry"].get("CALC_01", {}).get("state", {}).get("calcination_degree_pct"),
                "bzt_c": res["telemetry"].get("KILN_01", {}).get("state", {}).get("burning_zone_temp_c"),
                "free_lime_pct": res["telemetry"].get("KILN_01", {}).get("state", {}).get("free_lime_pct"),
                "clinker_tph": res["telemetry"].get("KILN_01", {}).get("state", {}).get("clinker_rate_tph"),
            },
        })

    # Restore nominal baseline at the end of verification
    apply_scenario(manager, "nominal_baseline")

    return {
        "total_scenarios": len(OPERATIONAL_SCENARIOS),
        "passed_scenarios": total_passed,
        "success_rate_pct": round((total_passed / max(1, len(OPERATIONAL_SCENARIOS))) * 100.0, 1),
        "all_passed": total_passed == len(OPERATIONAL_SCENARIOS),
        "results": summary,
    }
