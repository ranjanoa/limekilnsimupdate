"""
Comprehensive Test Suite for Kiln 3 Modular Flowsheet Builder & Engine.
Validates:
1. Block library classes, schemas, ports, and parameters
2. Graph connectivity, cycle detection, topological sorting, tear streams
3. Steady-state solver convergence and Wegstein acceleration
4. Dynamic ODE simulation stepping and conservation audits
5. All 4 pre-built templates
6. HTTP REST API endpoints
"""

import sys
import json
import unittest

from engine.modular.stream import ProcessStream, StreamPhase
from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.flowsheet_graph import FlowsheetGraph
from engine.modular.solver import FlowsheetSolver
from engine.modular.manager import ModularEngineManager
from engine.modular.library import (
    BLOCK_REGISTRY,
    get_block_class,
    get_component_catalog,
    GravimetricFeeder,
    FuelFeeder,
    SiloStorage,
    CycloneStage,
    CalcinerReactor,
    RotaryKiln,
    GrateCooler,
    IDFan,
    StreamMixer,
    StreamSplitter,
    DamperValve,
    FuelMixer,
    AirMixer,
    GasMixer,
)
from engine.modular.templates import (
    get_template_manifest,
    load_template_graph,
    TEMPLATE_BUILDERS,
)


class TestModularEngine(unittest.TestCase):

    def test_01_component_catalog(self):
        """Verify all 14 component blocks are properly registered and provide schemas."""
        self.assertEqual(len(BLOCK_REGISTRY), 14)
        catalog = get_component_catalog()
        self.assertEqual(len(catalog), 14)
        for item in catalog:
            self.assertIn("type", item)
            self.assertIn("category", item)
            self.assertIn("ports", item)
            self.assertIn("parameters", item)
            self.assertGreater(len(item["ports"]), 0)

    def test_02_stream_thermodynamics(self):
        """Verify ProcessStream thermodynamic enthalpy and volume flow calculation."""
        # Solid stream
        s_solid = ProcessStream(
            stream_id=1,
            name="Raw Meal",
            phase=StreamPhase.SOLID,
            mass_flow_tph=280.0,
            temperature_c=60.0,
        )
        self.assertGreater(s_solid.enthalpy_gjh, 0.0)
        self.assertAlmostEqual(s_solid.mass_flow_tph, 280.0)

        # Gas stream
        s_gas = ProcessStream(
            stream_id=2,
            name="Flue Gas",
            phase=StreamPhase.GAS,
            mass_flow_tph=378.0,
            temperature_c=330.0,
        )
        self.assertIsNotNone(s_gas.volume_flow_nm3h)
        self.assertGreater(s_gas.volume_flow_nm3h, 200000.0)

        # Fuel stream with chemical LHV
        s_fuel = ProcessStream(
            stream_id=3,
            name="Petcoke",
            phase=StreamPhase.FUEL,
            mass_flow_tph=10.0,
            temperature_c=25.0,
            composition={"lhv_mj_kg": 31.4},
        )
        self.assertGreater(s_fuel.enthalpy_gjh, 300.0)

    def test_03_graph_building_and_wiring(self):
        """Verify graph building, port-to-port wiring, and stream unbinding."""
        graph = FlowsheetGraph(flowsheet_id="test_graph", name="Test Graph")

        feeder = GravimetricFeeder(block_id="FEED_01", parameters={"nominal_rate_tph": 100.0})
        cyclone = CycloneStage(block_id="CYC_01")
        graph.add_block(feeder)
        graph.add_block(cyclone)

        stream = graph.connect("FEED_01", "out_solid", "CYC_01", "in_meal", name="Meal to C1")
        self.assertEqual(stream.stream_id, 1)
        self.assertEqual(cyclone.ports["in_meal"].connected_stream_id, 1)
        self.assertEqual(feeder.ports["out_solid"].connected_stream_id, 1)

        inlets = graph.get_block_inlets("CYC_01")
        self.assertIn("in_meal", inlets)
        self.assertEqual(inlets["in_meal"].stream_id, 1)

        # Disconnect
        graph.disconnect_stream(1)
        self.assertNotIn(1, graph.streams)
        self.assertIsNone(cyclone.ports["in_meal"].connected_stream_id)

    def test_04_templates_loading(self):
        """Verify all 5 pre-built templates load cleanly and have valid connections."""
        manifest = get_template_manifest()
        self.assertEqual(len(manifest), 5)

        for t in manifest:
            graph = load_template_graph(t["id"])
            self.assertGreater(len(graph.blocks), 0)
            self.assertGreater(len(graph.streams), 0)
            validation = graph.validate()
            self.assertTrue(validation["valid"], f"Validation failed for template '{t['id']}': {validation['errors']}")

    def test_05_steady_state_solver_convergence(self):
        """Verify sequential-modular steady-state solver converges Kiln 3 plant with Wegstein."""
        graph = load_template_graph("kiln_3_pyroprocess")
        solver = FlowsheetSolver(graph, tolerance=1e-4, max_iterations=40)
        res = solver.solve_steady_state()

        self.assertTrue(res["converged"], f"Solver did not converge! Max residual: {res['max_residual']}")
        self.assertGreater(res["iterations"], 0)
        self.assertGreater(res["tear_streams_count"], 0)

        audit = res["audit"]
        self.assertGreater(audit["mass_in_tph"], 200.0)
        self.assertGreater(audit["mass_out_tph"], 200.0)
        self.assertGreaterEqual(audit["mass_closure_pct"], 95.0)

    def test_06_dynamic_simulation_step(self):
        """Verify dynamic ODE stepping advances time and maintains stable telemetry."""
        graph = load_template_graph("kiln_3_pyroprocess")
        solver = FlowsheetSolver(graph)
        solver.solve_steady_state()

        for _ in range(10):
            step_res = solver.step(dt=0.5)

        self.assertAlmostEqual(solver.simulation_time_s, 5.0)
        self.assertEqual(solver.step_count, 10)
        self.assertGreater(step_res["audit"]["mass_in_tph"], 0)

    def test_07_modular_manager_api(self):
        """Verify ModularEngineManager methods for persistence, templates, and OPC tags."""
        mgr = ModularEngineManager()
        self.assertIsNotNone(mgr.active_graph)

        # Steady state solve on active graph
        act = mgr.get_active_flowsheet()
        self.assertIn("flowsheet", act)
        self.assertIn("stream_table", act)
        self.assertIn("audit", act)
        self.assertGreater(len(act["stream_table"]), 10)

        # Auto-generated OPC tags
        opc_tags = mgr.get_opc_tags()
        self.assertGreater(len(opc_tags), 20)
        for tag in opc_tags:
            self.assertIn("tag_id", tag)
            self.assertIn("node_id", tag)
            self.assertIn("access", tag)

        # Save and list
        save_res = mgr.save_to_file("test_plant_save.json", act["flowsheet"])
        self.assertEqual(save_res["status"], "success")

        saved_files = mgr.list_saved_files()
        self.assertTrue(any(f["filename"] == "test_plant_save.json" for f in saved_files))

    def test_08_operational_scenarios_sweep(self):
        """All canonical operating scenarios converge, close mass balance and meet physics checks."""
        from engine.modular.scenarios import verify_all_scenarios
        mgr = ModularEngineManager()
        report = verify_all_scenarios(mgr)
        failures = [
            (r["id"], [d for d in r.get("validation_details", []) if not d["passed"]], r.get("mass_closure_pct"))
            for r in report["results"] if not r["passed"]
        ]
        self.assertTrue(report["all_passed"], f"Scenario failures: {failures}")
        for r in report["results"]:
            self.assertGreaterEqual(r["mass_closure_pct"], 98.0, f"{r['id']} mass closure too low")

    def test_09_directional_process_interdependencies(self):
        """Each manipulated variable must move the coupled process states in the physically correct direction."""
        def run(overrides):
            mgr = ModularEngineManager()
            for (bid, p), v in overrides.items():
                mgr.update_block_parameter(bid, p, v)
            t = mgr.solver.get_blocks_telemetry()
            return {
                "t_pc": t["CALC_01"]["state"]["calciner_temp_c"],
                "alpha": t["CALC_01"]["state"]["calcination_degree_pct"],
                "bzt": t["KILN_01"]["state"]["burning_zone_temp_c"],
                "fcao": t["KILN_01"]["state"]["free_lime_pct"],
                "t_kg": t["KILN_01"]["state"]["kiln_inlet_gas_temp_c"],
                "clk_exit": t["COOLER_01"]["state"]["clinker_exit_temp_c"],
            }

        base = run({})
        low_feed = run({("FEED_01", "nominal_rate_tph"): 240.0})
        high_feed = run({("FEED_01", "nominal_rate_tph"): 310.0})
        low_kf = run({("FUEL_KILN", "nominal_rate_tph"): 6.2})
        high_kf = run({("FUEL_KILN", "nominal_rate_tph"): 8.2})
        low_pc = run({("FUEL_PC", "nominal_rate_tph"): 10.5})
        low_air = run({("COOLER_01", "cooling_air_total_tph"): 250.0})

        # Feed: less meal -> hotter calciner & burning zone; more meal -> colder
        self.assertGreater(low_feed["t_pc"], base["t_pc"])
        self.assertGreater(low_feed["bzt"], base["bzt"])
        self.assertLess(high_feed["t_pc"], base["t_pc"])
        self.assertLess(high_feed["alpha"], base["alpha"])
        # Kiln fuel: drives BZT, free lime (inverse) and kiln inlet gas temperature
        self.assertLess(low_kf["bzt"], base["bzt"])
        self.assertGreater(low_kf["fcao"], base["fcao"])
        self.assertLess(low_kf["t_kg"], base["t_kg"])
        self.assertGreater(high_kf["bzt"], base["bzt"])
        self.assertLess(high_kf["fcao"], base["fcao"])
        # PC fuel: drives calciner temperature and decarbonation
        self.assertLess(low_pc["t_pc"], base["t_pc"])
        self.assertLess(low_pc["alpha"], base["alpha"])
        # Cooler air: under-aeration -> hotter clinker discharge
        self.assertGreater(low_air["clk_exit"], base["clk_exit"])

    def test_10_fuel_mixer_sum_node(self):
        """Verify FuelMixer sum node correctly blends multi-fuel feeds (Coal + RDF) and feeds calciner."""
        # 1. Direct unit test of FuelMixer
        mixer = FuelMixer(block_id="SUM_01")
        fuel_coal = ProcessStream(
            stream_id=1,
            name="Primary Coal",
            phase=StreamPhase.FUEL,
            mass_flow_tph=8.0,
            temperature_c=25.0,
            composition={"lhv_mj_kg": 29.5, "ash_pct": 10.0, "moisture_pct": 2.0},
        )
        fuel_rdf = ProcessStream(
            stream_id=2,
            name="Fluff RDF",
            phase=StreamPhase.FUEL,
            mass_flow_tph=4.5,
            temperature_c=25.0,
            composition={"lhv_mj_kg": 18.5, "ash_pct": 14.5, "moisture_pct": 16.0},
        )

        inlets = {"in_fuel_1": fuel_coal, "in_fuel_2": fuel_rdf}
        outlets = mixer.evaluate_steady_state(inlets)
        self.assertIn("out_fuel", outlets)
        out_stream = outlets["out_fuel"]

        # Mass conservation: 8.0 + 4.5 = 12.5 t/h
        self.assertAlmostEqual(out_stream.mass_flow_tph, 12.5, places=3)
        # Weighted LHV: (8.0 * 29.5 + 4.5 * 18.5) / 12.5 = (236.0 + 83.25) / 12.5 = 319.25 / 12.5 = 25.54 MJ/kg
        expected_lhv = (8.0 * 29.5 + 4.5 * 18.5) / 12.5
        self.assertAlmostEqual(out_stream.composition["lhv_mj_kg"], expected_lhv, places=2)
        # TSR % = 83.25 / 319.25 * 100% = 26.077%
        expected_tsr = (4.5 * 18.5) / (8.0 * 29.5 + 4.5 * 18.5) * 100.0
        self.assertAlmostEqual(mixer.state["rdf_alt_fuel_share_pct"], expected_tsr, places=1)
        self.assertAlmostEqual(mixer.state["blended_lhv_mj_kg"], expected_lhv, places=2)

        # 2. Test dual_fuel_calciner_rdf template
        rdf_graph = load_template_graph("dual_fuel_calciner_rdf")
        self.assertEqual(len(rdf_graph.blocks), 9)
        self.assertEqual(len(rdf_graph.streams), 8)
        validation = rdf_graph.validate()
        self.assertTrue(validation["valid"], f"Validation failed: {validation['errors']}")

        # Steady-state solver convergence
        solver = FlowsheetSolver(rdf_graph)
        res = solver.solve_steady_state()
        self.assertTrue(res["converged"], f"RDF template did not converge! Max residual: {res.get('max_residual')}")

        calciner = rdf_graph.blocks["CALCINER"]
        self.assertGreater(calciner.state.get("calciner_temp_c", 0), 800.0)
        self.assertGreater(calciner.state.get("calcination_degree_pct", 0), 85.0)

    def test_11_air_and_gas_mixers(self):
        """Verify AirMixer and GasMixer sum nodes conserve mass, thermal enthalpy, and species."""
        # 1. Test AirMixer
        air_mixer = AirMixer(block_id="AIR_SUM_01")
        air_hot = ProcessStream(
            stream_id=1,
            name="Tertiary Air Takeoff",
            phase=StreamPhase.AIR,
            mass_flow_tph=120.0,
            temperature_c=850.0,
            composition={"O2_pct": 20.9, "N2_pct": 79.1},
        )
        air_leak = ProcessStream(
            stream_id=2,
            name="False Infiltration Air",
            phase=StreamPhase.AIR,
            mass_flow_tph=15.0,
            temperature_c=25.0,
            composition={"O2_pct": 20.9, "N2_pct": 79.1},
        )

        air_outlets = air_mixer.evaluate_steady_state({"in_air_1": air_hot, "in_air_2": air_leak})
        self.assertIn("out_air", air_outlets)
        out_air = air_outlets["out_air"]

        self.assertAlmostEqual(out_air.mass_flow_tph, 135.0, places=2)
        self.assertAlmostEqual(air_mixer.state["total_air_tph"], 135.0, places=2)
        # Blended temperature should be between 25 and 850
        self.assertGreater(out_air.temperature_c, 700.0)
        self.assertLess(out_air.temperature_c, 850.0)
        self.assertGreater(air_mixer.state["total_volume_nm3h"], 100000.0)
        self.assertAlmostEqual(air_mixer.state["blended_o2_pct"], 20.9, places=1)

        # 2. Test GasMixer
        gas_mixer = GasMixer(block_id="GAS_SUM_01")
        gas_kiln = ProcessStream(
            stream_id=3,
            name="Kiln Riser Flue Gas",
            phase=StreamPhase.GAS,
            mass_flow_tph=96.0,
            temperature_c=1050.0,
            composition={"CO2_pct": 24.5, "O2_pct": 2.2, "dust_concentration_g_nm3": 85.0},
        )
        gas_bypass = ProcessStream(
            stream_id=4,
            name="Calciner Exhaust Gas",
            phase=StreamPhase.GAS,
            mass_flow_tph=25.0,
            temperature_c=860.0,
            composition={"CO2_pct": 32.0, "O2_pct": 3.8, "dust_concentration_g_nm3": 40.0},
        )

        gas_outlets = gas_mixer.evaluate_steady_state({"in_gas_1": gas_kiln, "in_gas_2": gas_bypass})
        self.assertIn("out_gas", gas_outlets)
        out_gas = gas_outlets["out_gas"]

        self.assertAlmostEqual(out_gas.mass_flow_tph, 121.0, places=2)
        self.assertAlmostEqual(gas_mixer.state["total_gas_tph"], 121.0, places=2)
        self.assertGreater(out_gas.temperature_c, 900.0)
        self.assertLess(out_gas.temperature_c, 1050.0)
        # Weighted CO2: (96 * 24.5 + 25 * 32.0) / 121 = (2352 + 800) / 121 = 26.05%
        expected_co2 = (96.0 * 24.5 + 25.0 * 32.0) / 121.0
        self.assertAlmostEqual(gas_mixer.state["blended_co2_pct"], expected_co2, places=1)
        self.assertGreater(gas_mixer.state["total_volume_nm3h"], 80000.0)

    def test_12_configurable_feed_composition(self):
        """Verify user-defined feed mineral assay propagates to downstream reactors."""
        # 1. Gravimetric feeder with custom high-purity limestone (e.g. Lime Kiln)
        feeder = GravimetricFeeder(
            block_id="FEED_CUSTOM",
            parameters={
                "nominal_rate_tph": 180.0,
                "caco3_pct": 94.5,
                "mgco3_pct": 1.8,
                "sio2_pct": 2.2,
                "al2o3_pct": 0.6,
                "fe2o3_pct": 0.4,
                "moisture_pct": 1.2,
            }
        )
        feeder.initialize()
        out_solid = ProcessStream(stream_id=1, name="Custom Stone Feed", phase=StreamPhase.SOLID)
        outlets = feeder.evaluate_steady_state({}, {"out_solid": out_solid})

        # Check feeder state & stream composition
        self.assertEqual(feeder.state["caco3_pct"], 94.5)
        # LOI = 94.5 * 0.43971 + 1.8 * 0.52197 = 41.55 + 0.94 = 42.49%
        self.assertAlmostEqual(feeder.state["loi_pct"], 42.49, delta=0.5)
        self.assertEqual(out_solid.composition["CaCO3_pct"], 94.5)
        self.assertEqual(out_solid.composition["SiO2_pct"], 2.2)

        # 2. Rotary Kiln calcining high-calcium limestone into quicklime
        kiln = RotaryKiln(
            block_id="LIME_KILN_01",
            parameters={"target_burning_zone_c": 1280.0}
        )
        kiln.initialize()
        fuel_gas = ProcessStream(stream_id=2, name="Natural Gas", phase=StreamPhase.FUEL, mass_flow_tph=6.5, composition={"lhv_mj_kg": 46.5})
        air_sec = ProcessStream(stream_id=3, name="Secondary Air", phase=StreamPhase.AIR, mass_flow_tph=120.0, temperature_c=650.0)
        out_lime = ProcessStream(stream_id=4, name="Discharge Quicklime", phase=StreamPhase.SOLID)
        out_gas = ProcessStream(stream_id=5, name="Kiln Gas", phase=StreamPhase.GAS)

        inlets = {"in_meal_calcined": out_solid, "in_flame_fuel": fuel_gas, "in_secondary_air": air_sec}
        kiln_outlets = kiln.evaluate_steady_state(inlets, {"out_clinker": out_lime, "out_kiln_gas": out_gas})

        # Check quicklime production
        self.assertIn("out_clinker", kiln_outlets)
        self.assertIn("Active_CaO_pct", out_lime.composition)
        self.assertGreaterEqual(out_lime.composition["Active_CaO_pct"], 90.0)

    def test_13_rename_block_and_opc_tags(self):
        """Verify renaming a block updates connections and OPC UA node IDs."""
        from engine.modular.manager import ModularEngineManager
        mgr = ModularEngineManager()
        tpl = mgr.get_template_data("single_cyclone_demo")
        mgr.load_graph_data(tpl)

        # Verify old block ID exists in graph and OPC tags
        self.assertIn("FEED_01", mgr.active_graph.blocks)
        opc_tags_before = mgr.get_opc_tags()
        node_ids_before = [t["node_id"] for t in opc_tags_before]
        self.assertTrue(any("FEED_01" in nid for nid in node_ids_before))

        # Rename block to unique custom ID
        res = mgr.rename_block("FEED_01", "CUSTOM_FEEDER_99")
        self.assertEqual(res["status"], "success")

        # Verify block ID changed in graph
        self.assertNotIn("FEED_01", mgr.active_graph.blocks)
        self.assertIn("CUSTOM_FEEDER_99", mgr.active_graph.blocks)

        # Verify stream connections updated to new block ID
        feed_stream = next(s for s in mgr.active_graph.streams.values() if s.from_block == "CUSTOM_FEEDER_99")
        self.assertEqual(feed_stream.from_block, "CUSTOM_FEEDER_99")

        # Verify OPC UA node IDs updated to new block ID
        opc_tags_after = mgr.get_opc_tags()
        node_ids_after = [t["node_id"] for t in opc_tags_after]
        self.assertFalse(any("FEED_01" in nid for nid in node_ids_after))
        self.assertTrue(any("CUSTOM_FEEDER_99" in nid for nid in node_ids_after))


if __name__ == "__main__":
    unittest.main()



