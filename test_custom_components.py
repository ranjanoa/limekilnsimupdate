"""
Unit Tests for Custom Component Dynamic Loader and Auto-Registration.
Validates:
1. Validation of custom BlockBase source code (syntax, ports, schemas, steady-state)
2. All 6 curated starter templates pass validation
3. Save, auto-discovery, dynamic registration into BLOCK_REGISTRY
4. Integration with FlowsheetGraph, solver, dynamic ODE step, and OPC UA tag generation
5. Deletion and cleanup
"""

import os
import unittest

from engine.modular.library import (
    BLOCK_REGISTRY,
    CUSTOM_BLOCK_REGISTRY,
    get_block_class,
    get_component_catalog,
    validate_component_source,
    save_and_register_custom_component,
    delete_custom_component,
    get_custom_components_list,
    get_available_templates,
    load_custom_components,
)
from engine.modular.stream import ProcessStream, StreamPhase
from engine.modular.flowsheet_graph import FlowsheetGraph
from engine.modular.solver import FlowsheetSolver


class TestCustomComponents(unittest.TestCase):

    def test_01_all_starter_templates_valid(self):
        """Verify all curated starter templates compile and pass validation."""
        templates = get_available_templates()
        self.assertGreaterEqual(len(templates), 5)
        for tpl in templates:
            res = validate_component_source(tpl["code"])
            self.assertTrue(
                res.get("valid"),
                f"Template '{tpl['name']}' failed validation: {res.get('error')}",
            )
            self.assertIn("ports", res)
            self.assertGreater(len(res["ports"]), 0)
            self.assertIn("parameters", res)

    def test_02_validation_catches_syntax_and_schema_errors(self):
        """Verify code validator catches syntax errors, missing ports, and non-BlockBase code."""
        # 1. Syntax Error
        bad_syntax = "class BrokenBlock(BlockBase:\n    pass"
        res1 = validate_component_source(bad_syntax)
        self.assertFalse(res1.get("valid"))
        self.assertIn("Syntax Error", res1.get("error"))

        # 2. Not inheriting from BlockBase
        not_block = "class StandaloneClass:\n    pass"
        res2 = validate_component_source(not_block)
        self.assertFalse(res2.get("valid"))
        self.assertIn("No subclass of BlockBase found", res2.get("error"))

        # 3. Missing ports
        no_ports = '''
from engine.modular.block_base import BlockBase
class EmptyPortsBlock(BlockBase):
    block_type = "EmptyPortsBlock"
    def _define_ports(self): return []
    def _define_parameters(self): return {}
    def evaluate_steady_state(self, in_s, out_s): return out_s
'''
        res3 = validate_component_source(no_ports)
        self.assertFalse(res3.get("valid"))
        self.assertIn("zero ports", res3.get("error"))

    def test_03_save_register_and_simulate_custom_component(self):
        """Verify a custom component can be saved, auto-registered, simulated, and deleted."""
        custom_code = '''"""
Custom Biomass Gasifier Unit
"""
from typing import Dict, List, Any
import copy
from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase

class BiomassGasifier(BlockBase):
    block_type = "BiomassGasifier"
    category = "Combustion"
    icon = "🔥"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_biomass", PortDirection.IN, StreamPhase.SOLID, "Biomass chips feed"),
            Port("out_syngas", PortDirection.OUT, StreamPhase.GAS, "Clean syngas fuel"),
            Port("out_biochar", PortDirection.OUT, StreamPhase.SOLID, "Biochar residue"),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "gasification_temp_c": {"type": float, "default": 850.0, "min": 600.0, "max": 1200.0, "unit": "°C"},
            "syngas_yield_pct": {"type": float, "default": 72.0, "min": 20.0, "max": 95.0, "unit": "%"},
        }

    def initialize(self):
        self.state = {
            "syngas_rate_nm3h": 4500.0,
            "char_rate_tph": 2.8,
            "gasifier_temp_c": 850.0,
        }

    def evaluate_steady_state(self, inlet_streams, outlet_streams):
        in_bio = inlet_streams.get("in_biomass")
        out_gas = outlet_streams.get("out_syngas")
        out_char = outlet_streams.get("out_biochar")

        m_in = in_bio.mass_flow_tph if in_bio else 10.0
        yield_pct = float(self.parameters.get("syngas_yield_pct", 72.0)) / 100.0
        t_op = float(self.parameters.get("gasification_temp_c", 850.0))

        m_gas = m_in * yield_pct
        m_char = m_in * (1.0 - yield_pct)
        v_gas = (m_gas * 1000.0) / 1.15

        self.state["syngas_rate_nm3h"] = round(v_gas, 1)
        self.state["char_rate_tph"] = round(m_char, 2)
        self.state["gasifier_temp_c"] = round(t_op, 1)

        if out_gas:
            out_gas.update_state(mass_flow_tph=m_gas, volume_flow_nm3h=v_gas, temperature_c=t_op, pressure_mbar=5.0)
        if out_char:
            out_char.update_state(mass_flow_tph=m_char, temperature_c=t_op - 100.0, pressure_mbar=0.0)
        return outlet_streams
'''
        # 1. Save and register
        res = save_and_register_custom_component(custom_code, BLOCK_REGISTRY, "biomass_gasifier.py")
        self.assertTrue(res.get("valid"))
        self.assertEqual(res.get("block_type"), "BiomassGasifier")
        self.assertIn("BiomassGasifier", BLOCK_REGISTRY)

        # 2. Check catalog contains custom indicator
        catalog = get_component_catalog()
        custom_items = [c for c in catalog if c["type"] == "BiomassGasifier"]
        self.assertEqual(len(custom_items), 1)
        self.assertTrue(custom_items[0].get("is_custom"))
        self.assertEqual(custom_items[0]["icon"], "🔥")

        # 3. Instantiate and simulate within a FlowsheetGraph
        graph = FlowsheetGraph(name="Custom Block Integration Test")
        cls = get_block_class("BiomassGasifier")
        unit = cls(block_id="GASIFIER_01")
        graph.add_block(unit)

        # Check ports
        self.assertEqual(len(unit.ports), 3)
        self.assertIn("in_biomass", unit.ports)

        # Set parameter
        unit.set_parameter("gasification_temp_c", 900.0)
        self.assertEqual(unit.parameters["gasification_temp_c"], 900.0)

        # Check OPC UA auto-generated tags
        tags = unit.get_opc_tags()
        self.assertGreater(len(tags), 0)
        self.assertTrue(any(t["tag_id"] == "GASIFIER_01_GASIFIER_TEMP_C" for t in tags))

        # Test solver step
        solver = FlowsheetSolver(graph)
        solve_res = solver.solve_steady_state()
        self.assertTrue(solve_res.get("converged"))

        # 4. Clean up / delete custom component
        deleted = delete_custom_component("BiomassGasifier", BLOCK_REGISTRY)
        self.assertTrue(deleted)
        self.assertNotIn("BiomassGasifier", BLOCK_REGISTRY)
        self.assertNotIn("BiomassGasifier", CUSTOM_BLOCK_REGISTRY)

    def test_04_http_rest_api_endpoints(self):
        """Verify REST API endpoints for templates, validate, save, list, reload, delete."""
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from server import SimulatorRestHttpHandler
        import json

        # Start temporary server on an ephemeral port
        server = ThreadingHTTPServer(("127.0.0.1", 0), SimulatorRestHttpHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. GET templates
            with urllib.request.urlopen(f"{base_url}/api/flowsheet/builder/custom_components/templates") as resp:
                self.assertEqual(resp.status, 200)
                tpls = json.loads(resp.read().decode("utf-8"))
                self.assertGreaterEqual(len(tpls), 5)

            # 2. POST validate
            sample_code = tpls[0]["code"]
            req = urllib.request.Request(
                f"{base_url}/api/flowsheet/builder/custom_components/validate",
                data=json.dumps({"code": sample_code}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                val_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(val_data.get("valid"))

            # 3. POST save
            test_py = '''"""
HTTP Test Block
"""
from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase

class HttpTestBlock(BlockBase):
    block_type = "HttpTestBlock"
    category = "Custom"
    icon = "🧪"
    def _define_ports(self):
        return [
            Port("in_port", PortDirection.IN, StreamPhase.GAS),
            Port("out_port", PortDirection.OUT, StreamPhase.GAS),
        ]
    def _define_parameters(self):
        return {"factor": {"type": float, "default": 1.0}}
    def evaluate_steady_state(self, ins, outs):
        return outs
'''
            save_req = urllib.request.Request(
                f"{base_url}/api/flowsheet/builder/custom_components",
                data=json.dumps({"code": test_py, "filename": "http_test_block.py"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(save_req) as resp:
                self.assertEqual(resp.status, 200)
                save_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(save_data.get("valid"))
                self.assertEqual(save_data.get("block_type"), "HttpTestBlock")

            # 4. GET custom components list
            with urllib.request.urlopen(f"{base_url}/api/flowsheet/builder/custom_components") as resp:
                self.assertEqual(resp.status, 200)
                comp_list = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(any(c["type"] == "HttpTestBlock" for c in comp_list))

            # 5. POST reload
            reload_req = urllib.request.Request(
                f"{base_url}/api/flowsheet/builder/custom_components/reload",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(reload_req) as resp:
                self.assertEqual(resp.status, 200)
                reload_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(reload_data.get("status"), "success")

            # 6. POST delete
            del_req = urllib.request.Request(
                f"{base_url}/api/flowsheet/builder/custom_components/delete",
                data=json.dumps({"block_type": "HttpTestBlock"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(del_req) as resp:
                self.assertEqual(resp.status, 200)
                del_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(del_data.get("status"), "success")

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
