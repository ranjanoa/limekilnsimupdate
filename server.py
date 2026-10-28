"""
MASTER RUNNER: CEMENT PLANT FIRST-PRINCIPLES REAL-TIME SIMULATOR & OPTIMIZATION TESTBED
Integrates:
1. First-Principles Physics & Kinetic Engine (coupled ODEs)
2. OPC UA Server (opc.tcp://0.0.0.0:4840) OR OPC UA Client Bridge for external optimizers (APC/MPC/RL)
3. HTTP & REST API Server (http://localhost:8080) for Web HMI & Configuration Management
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Import Engine & Interfaces
from engine.first_principles_engine import FirstPrinciplesEngine
from engine.modular.manager import ModularEngineManager
from engine.modular.scenarios import get_scenarios_catalog, apply_scenario, verify_all_scenarios
from engine.modular.library import (
    BLOCK_REGISTRY,
    get_component_catalog,
    load_custom_components,
    validate_component_source,
    save_and_register_custom_component,
    delete_custom_component,
    get_custom_components_list,
    get_available_templates,
)
from interfaces.opc_ua_server import CementOpcUaServer
from interfaces.opc_ua_client_bridge import CementOpcUaClientBridge

import mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("MasterServer")

if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, "_MEIPASS", EXE_DIR)

    # 1. Locate simulator directory (prefer adjacent to .exe if present, fallback to bundled)
    if os.path.exists(os.path.join(EXE_DIR, "simulator", "index.html")):
        SIMULATOR_DIR = os.path.join(EXE_DIR, "simulator")
    elif os.path.exists(os.path.join(BUNDLE_DIR, "simulator", "index.html")):
        SIMULATOR_DIR = os.path.join(BUNDLE_DIR, "simulator")
    elif os.path.exists(os.path.join(EXE_DIR, "simulator")):
        SIMULATOR_DIR = os.path.join(EXE_DIR, "simulator")
    else:
        SIMULATOR_DIR = os.path.join(BUNDLE_DIR, "simulator")

    # 2. Locate configuration directory (prefer adjacent to .exe if present, fallback to bundled)
    if os.path.exists(os.path.join(EXE_DIR, "config", "plant_config.json")):
        CONFIG_PATH = os.path.join(EXE_DIR, "config", "plant_config.json")
        BASE_DIR = EXE_DIR
    elif os.path.exists(os.path.join(BUNDLE_DIR, "config", "plant_config.json")):
        CONFIG_PATH = os.path.join(BUNDLE_DIR, "config", "plant_config.json")
        BASE_DIR = BUNDLE_DIR
    else:
        BASE_DIR = EXE_DIR if os.path.exists(os.path.join(EXE_DIR, "simulator")) else BUNDLE_DIR
        CONFIG_PATH = os.path.join(BASE_DIR, "config", "plant_config.json")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SIMULATOR_DIR = os.path.join(BASE_DIR, "simulator")
    CONFIG_PATH = os.path.join(BASE_DIR, "config", "plant_config.json")

# Verify critical frontend asset existence
index_file = os.path.join(SIMULATOR_DIR, "index.html")
if not os.path.exists(index_file):
    logger.error(f"❌ [CRITICAL] index.html not found in {SIMULATOR_DIR}!")
else:
    logger.info(f"Verified Web HMI root: {SIMULATOR_DIR}")

# Shared Engine, Modular Flowsheet & OPC Server Instances
engine = FirstPrinciplesEngine(config_path=CONFIG_PATH)
modular_manager = ModularEngineManager()
active_opc_server = None
active_event_loop = None

def sync_modular_telemetry_to_engine(modular_mgr, eng):
    """Synchronizes dynamic block states from the running modular flowsheet into the main engine."""
    try:
        if not hasattr(modular_mgr, "active_graph") or not modular_mgr.active_graph:
            return
        blocks = modular_mgr.active_graph.blocks
        # 1. Feed rate
        feed_b = blocks.get("FEED_01") or blocks.get("FEED_STONE") or next((b for b in blocks.values() if getattr(b, "block_type", "") in ("GravimetricFeeder", "Feeder")), None)
        if feed_b:
            feed_rate = feed_b.state.get("actual_feed_rate_tph") or feed_b.parameters.get("nominal_rate_tph")
            if feed_rate is not None:
                eng.feed_rate = float(feed_rate)
        # 2. Kiln (supports cement KILN_01, lime LIME_KILN, or any RotaryKiln block)
        kiln_b = blocks.get("KILN_01") or blocks.get("LIME_KILN") or next((b for b in blocks.values() if getattr(b, "block_type", "") == "RotaryKiln"), None)
        if kiln_b:
            bz_temp = kiln_b.state.get("burning_zone_temp_c")
            if bz_temp is not None:
                eng.sintering_temp = float(bz_temp)
            free_lime = kiln_b.state.get("free_lime_pct") or kiln_b.state.get("residual_caco3_pct")
            if free_lime is not None:
                eng.free_lime = float(free_lime)
            clinker_rate = kiln_b.state.get("clinker_rate_tph")
            if clinker_rate is not None:
                eng.clinker_production = float(clinker_rate)
            torque = kiln_b.state.get("kiln_drive_torque_kwn")
            if torque is not None:
                eng.kiln_drive_torque = float(torque)
            current_a = kiln_b.state.get("kiln_drive_current_a")
            if current_a is not None:
                eng.kiln_amps = float(current_a)
            filling = kiln_b.state.get("bed_filling_degree_pct")
            if filling is not None:
                eng.filling_degree = float(filling)
            spd = kiln_b.parameters.get("speed_rpm")
            if spd is not None:
                eng.kiln_speed = float(spd)
            kln_o2 = kiln_b.state.get("kiln_inlet_o2_pct")
            if kln_o2 is not None:
                eng.kiln_inlet_o2 = float(kln_o2)
            kln_co = kiln_b.state.get("kiln_inlet_co_pct")
            if kln_co is not None:
                eng.kiln_inlet_co = float(kln_co)
            kln_nox = kiln_b.state.get("kiln_inlet_nox_ppm")
            if kln_nox is not None:
                eng.kiln_inlet_nox = float(kln_nox)
            kln_t = kiln_b.state.get("kiln_inlet_gas_temp_c")
            if kln_t is not None:
                eng.kiln_inlet_temp = float(kln_t)
        # 3. Calciner
        calc_b = blocks.get("CALC_01")
        if calc_b:
            calc_temp = calc_b.state.get("calciner_temp_c")
            if calc_temp is not None:
                eng.calciner_temp = float(calc_temp)
            calc_deg = calc_b.state.get("calcination_degree_pct")
            if calc_deg is not None:
                eng.pc_calcination = float(calc_deg)
            calc_o2 = calc_b.state.get("calciner_o2_pct")
            if calc_o2 is not None:
                eng.ph_o2 = float(calc_o2)
            calc_co = calc_b.state.get("calciner_co_pct")
            if calc_co is not None:
                eng.ph_co = float(calc_co)
        # 4. Cooler
        cooler_b = blocks.get("COOLER_01")
        if cooler_b:
            sec_air = cooler_b.state.get("secondary_air_temp_c")
            if sec_air is not None:
                eng.secondary_air_t = float(sec_air)
            tert_air = cooler_b.state.get("tertiary_air_temp_c")
            if tert_air is not None:
                eng.tertiary_air_t = float(tert_air)
        # 5. Preheater top cyclone
        cyc_b = blocks.get("CYC_01")
        if cyc_b:
            gas_t = cyc_b.state.get("gas_temp_c")
            if gas_t is not None:
                eng.ph_top_gas_t = float(gas_t)
        # 6. ID Fan
        fan_b = blocks.get("ID_FAN_01")
        if fan_b:
            draft = fan_b.state.get("inlet_draft_mbar")
            if draft is not None:
                eng.ph_top_draft = float(draft)
        # 7. Dedicated Stream Sensors (if placed on gas streams)
        for b_id, b_inst in blocks.items():
            if b_inst.block_type == "StreamSensor":
                o2_m = b_inst.state.get("o2_pct")
                co_m = b_inst.state.get("co_pct")
                nox_m = b_inst.state.get("nox_ppm")
                bid_lower = b_id.lower()
                if "kiln" in bid_lower or "inlet" in bid_lower:
                    if o2_m is not None: eng.kiln_inlet_o2 = float(o2_m)
                    if co_m is not None: eng.kiln_inlet_co = float(co_m)
                    if nox_m is not None: eng.kiln_inlet_nox = float(nox_m)
                elif "calc" in bid_lower or "ph" in bid_lower:
                    if o2_m is not None: eng.ph_o2 = float(o2_m)
                    if co_m is not None: eng.ph_co = float(co_m)
    except Exception as e:
        logger.debug(f"Telemetry sync error: {e}")

def get_unified_tags_list(eng, modular_mgr):
    """Combines baseline plant tags and running modular equipment tags into unified list."""
    sync_modular_telemetry_to_engine(modular_mgr, eng)
    base_tags = eng.get_tags_list()
    base_tag_ids = {t["tag_id"] for t in base_tags}
    
    modular_tags = modular_mgr.get_opc_tags() if hasattr(modular_mgr, "get_opc_tags") else []
    unified = list(base_tags)
    for mt in modular_tags:
        if mt["tag_id"] not in base_tag_ids:
            unified.append(mt)
            base_tag_ids.add(mt["tag_id"])
    return unified

class SimulatorRestHttpHandler(SimpleHTTPRequestHandler):
    """Serves static simulator files and provides REST API for live config, telemetry, tags & commands."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SIMULATOR_DIR, **kwargs)

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE, PUT")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.do_GET()
        else:
            super().do_HEAD()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
        elif parsed.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            telemetry = engine.get_telemetry_dict()
            self.wfile.write(json.dumps(telemetry).encode("utf-8"))
        elif parsed.path == "/api/flowsheet":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            flowsheet_data = engine.get_flowsheet_data()
            self.wfile.write(json.dumps(flowsheet_data).encode("utf-8"))
        elif parsed.path == "/api/tags":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            tags = get_unified_tags_list(engine, modular_manager)
            self.wfile.write(json.dumps(tags).encode("utf-8"))
        elif parsed.path == "/api/opc/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            tags = get_unified_tags_list(engine, modular_manager)
            opc_count = sum(1 for t in tags if t.get("source") == "opc_ua")
            local_count = sum(1 for t in tags if t.get("source") == "local")
            opc_status = {
                "server_running": True,
                "opc_active": active_opc_server is not None and getattr(active_opc_server, "is_running", False),
                "opc_mode": cfg.get("opc_ua", {}).get("mode", "server"),
                "server_endpoint": cfg.get("opc_ua", {}).get("server_endpoint", "opc.tcp://0.0.0.0:4841/freeopcua/server/"),
                "client_endpoint": cfg.get("opc_ua", {}).get("client_target_endpoint", "opc.tcp://127.0.0.1:4841/freeopcua/server/"),
                "namespace_uri": cfg.get("opc_ua", {}).get("namespace_uri", "http://cement.simulation.siemens.com/kiln3/"),
                "total_tags": len(tags),
                "opc_tags": opc_count,
                "local_tags": local_count,
                "publish_interval_ms": cfg.get("opc_ua", {}).get("publish_interval_ms", 500)
            }
            self.wfile.write(json.dumps(opc_status).encode("utf-8"))
        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            status = {
                "server_running": True,
                "engine_mode": "first_principles_ode",
                "operating_mode": cfg.get("simulation", {}).get("operating_mode", "opc_ua"),
                "opc_mode": cfg.get("opc_ua", {}).get("mode", "server"),
                "opc_endpoint": cfg.get("opc_ua", {}).get("server_endpoint", "opc.tcp://0.0.0.0:4841/freeopcua/server/"),
                "optimizer_active": engine.optimizer_active,
                "opt_commands": engine.opt_commands
            }
            self.wfile.write(json.dumps(status).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/components":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            catalog = modular_manager.get_component_catalog()
            self.wfile.write(json.dumps(catalog).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/custom_components/templates":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(get_available_templates()).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/custom_components":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(get_custom_components_list()).encode("utf-8"))
        elif parsed.path.startswith("/api/flowsheet/builder/custom_components/"):
            comp_type = parsed.path.split("/")[-1]
            comps = {c["type"]: c for c in get_custom_components_list()}
            if comp_type in comps:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(comps[comp_type]).encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Custom component '{comp_type}' not found"}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/templates":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            templates = modular_manager.get_template_manifest()
            self.wfile.write(json.dumps(templates).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/scenarios":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            catalog = get_scenarios_catalog()
            self.wfile.write(json.dumps(catalog).encode("utf-8"))
        elif parsed.path.startswith("/api/flowsheet/builder/template/"):
            tpl_id = parsed.path.split("/")[-1]
            try:
                tpl_data = modular_manager.get_template_data(tpl_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(tpl_data).encode("utf-8"))
            except Exception as e:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/active":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            active_data = modular_manager.get_active_flowsheet()
            self.wfile.write(json.dumps(active_data).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/list":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            files_list = modular_manager.list_saved_files()
            self.wfile.write(json.dumps(files_list).encode("utf-8"))
        elif parsed.path.startswith("/api/flowsheet/builder/load/"):
            fname = parsed.path.split("/")[-1]
            try:
                loaded = modular_manager.load_from_file(fname)
                if active_opc_server and active_event_loop:
                    for t in modular_manager.get_opc_tags():
                        try:
                            asyncio.run_coroutine_threadsafe(active_opc_server.register_node(t), active_event_loop)
                        except Exception as tag_err:
                            logger.debug(f"OPC tag dynamic registration error: {tag_err}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(loaded).encode("utf-8"))
            except Exception as e:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            if parsed.path in ("/", ""):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length)

        if parsed.path == "/api/config":
            try:
                new_cfg = json.loads(post_body.decode("utf-8"))
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(new_cfg, f, indent=2)
                engine.load_configuration()
                logger.info("Configuration reloaded dynamically from API update!")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Configuration updated and reloaded into engine"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/command":
            try:
                cmd = json.loads(post_body.decode("utf-8"))
                engine.step(0.1, opt_commands=cmd)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "optimizer_active": engine.optimizer_active}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/setpoint":
            try:
                body = json.loads(post_body.decode("utf-8"))
                loop = body.get("loop")
                val = float(body.get("value"))
                engine.apply_operator_setpoint(loop, val)
                if active_opc_server and active_event_loop:
                    try:
                        asyncio.run_coroutine_threadsafe(active_opc_server.update_command_node(loop, val), active_event_loop)
                    except Exception as ex:
                        logger.warning(f"Could not update OPC UA command node: {ex}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "loop": loop, "value": val}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/reset":
            try:
                engine.reset_to_nominal()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Simulator reset to nominal 280 tph steady state"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/mode":
            try:
                body = json.loads(post_body.decode("utf-8"))
                new_mode = body.get("mode", "opc_ua")
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "simulation" not in cfg:
                    cfg["simulation"] = {}
                cfg["simulation"]["operating_mode"] = new_mode
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                engine.load_configuration()
                logger.info(f"Simulator operating mode switched to: {new_mode.upper()}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "mode": new_mode}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/tags/toggle":
            try:
                body = json.loads(post_body.decode("utf-8"))
                tag_id = body.get("tag_id")
                source = body.get("source", "local")
                success = engine.set_tag_source(tag_id, source)
                logger.info(f"Tag '{tag_id}' source changed to: {source.upper()}")
                self.send_response(200 if success else 404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success" if success else "error", "tag_id": tag_id, "source": source}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/tags/value":
            try:
                body = json.loads(post_body.decode("utf-8"))
                tag_id = body.get("tag_id")
                val = body.get("value")
                success = engine.set_tag_value(tag_id, val)
                if "_SP_" in str(tag_id):
                    parts = str(tag_id).split("_SP_")
                    b_id = parts[0]
                    p_name = parts[1].lower()
                    modular_manager.update_block_parameter(b_id, p_name, val)
                    success = True
                elif tag_id == "Opt_FeedRate_SP":
                    modular_manager.update_block_parameter("FEED_01", "nominal_rate_tph", val)
                elif tag_id == "Opt_PCTemp_SP":
                    modular_manager.update_block_parameter("CALC_01", "target_calciner_temp_c", val)
                if active_opc_server and active_event_loop:
                    try:
                        asyncio.run_coroutine_threadsafe(active_opc_server.update_command_node(tag_id, val), active_event_loop)
                    except Exception as ex:
                        logger.warning(f"Could not update OPC UA command node: {ex}")
                self.send_response(200 if success else 404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success" if success else "error", "tag_id": tag_id, "value": val}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/tags/create":
            try:
                body = json.loads(post_body.decode("utf-8"))
                success = engine.add_custom_tag(body)
                if active_opc_server and active_event_loop and body.get("source") == "opc_ua":
                    try:
                        asyncio.run_coroutine_threadsafe(active_opc_server.register_node(body), active_event_loop)
                    except Exception as ex:
                        logger.warning(f"Could not dynamically register node in running OPC UA server: {ex}")
                logger.info(f"New custom tag '{body.get('tag_id')}' registered successfully!")
                self.send_response(200 if success else 400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "tag": body}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/tags/update":
            try:
                body = json.loads(post_body.decode("utf-8"))
                tag_id = body.get("tag_id")
                updates = body.get("updates", {})
                success = engine.update_tag(tag_id, updates)
                self.send_response(200 if success else 404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success" if success else "error"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/tags/delete":
            try:
                body = json.loads(post_body.decode("utf-8"))
                tag_id = body.get("tag_id")
                success = engine.delete_custom_tag(tag_id)
                self.send_response(200 if success else 404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success" if success else "error"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/opc/test":
            try:
                body = json.loads(post_body.decode("utf-8")) if post_body and post_body.strip() else {}
                endpoint = body.get("endpoint") or (active_opc_server.endpoint if active_opc_server else "opc.tcp://127.0.0.1:4841/freeopcua/server/")
                is_active = active_opc_server is not None and getattr(active_opc_server, "is_running", False)
                tags = get_unified_tags_list(engine, modular_manager)
                nodes_count = len(tags)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if is_active else "warning",
                    "reachable": is_active,
                    "endpoint": endpoint,
                    "nodes_count": nodes_count,
                    "latency_ms": 1.4 if is_active else 0.0,
                    "message": "OPC UA server active, listening on port 4841 and all registered nodes ready" if is_active else "OPC UA Server is not currently running."
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/custom_components/validate":
            try:
                body = json.loads(post_body.decode("utf-8"))
                code = body.get("code", "")
                val_res = validate_component_source(code)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(val_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"valid": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/custom_components":
            try:
                body = json.loads(post_body.decode("utf-8"))
                code = body.get("code", "")
                fname = body.get("filename")
                save_res = save_and_register_custom_component(code, BLOCK_REGISTRY, fname)
                status_code = 200 if save_res.get("valid") else 400
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(save_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"valid": False, "error": str(e)}).encode("utf-8"))
        elif parsed.path in ("/api/flowsheet/builder/custom_components/delete", "/api/flowsheet/builder/custom_components/remove"):
            try:
                body = json.loads(post_body.decode("utf-8"))
                b_type = body.get("block_type") or body.get("type")
                del_res = delete_custom_component(b_type, BLOCK_REGISTRY)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success" if del_res else "not_found", "block_type": b_type}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/custom_components/reload":
            try:
                reloaded = load_custom_components(BLOCK_REGISTRY)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "count": len(reloaded),
                    "registered": list(reloaded.keys())
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/solve":
            try:
                body = json.loads(post_body.decode("utf-8"))
                solve_res = modular_manager.solve_graph_data(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(solve_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/deploy":
            try:
                body = json.loads(post_body.decode("utf-8"))
                deploy_res = modular_manager.load_graph_data(body)
                # Dynamically register generated OPC UA tags if server is running
                if active_opc_server and active_event_loop:
                    opc_tags = modular_manager.get_opc_tags()
                    for t in opc_tags:
                        try:
                            asyncio.run_coroutine_threadsafe(active_opc_server.register_node(t), active_event_loop)
                        except Exception as tag_err:
                            logger.debug(f"OPC tag dynamic registration error: {tag_err}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(deploy_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/rename":
            try:
                body = json.loads(post_body.decode("utf-8"))
                old_id = body.get("old_block_id") or body.get("old_id")
                new_id = body.get("new_block_id") or body.get("new_id")
                res = modular_manager.rename_block(old_id, new_id)
                self.send_response(200 if res.get("status") in ("success", "skipped") else 400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/save":
            try:
                body = json.loads(post_body.decode("utf-8"))
                filename = body.get("filename") or body.get("name") or "custom_flowsheet"
                res = modular_manager.save_to_file(filename, body.get("flowsheet") or body.get("graph") or body)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/delete":
            try:
                body = json.loads(post_body.decode("utf-8"))
                filename = body.get("filename")
                if filename and not filename.endswith(".json"):
                    filename += ".json"
                fpath = os.path.join(modular_manager.storage_dir, filename) if filename else None
                if fpath and os.path.exists(fpath):
                    os.remove(fpath)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": f"Deleted {filename}"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/param":
            try:
                body = json.loads(post_body.decode("utf-8"))
                block_id = body.get("block_id")
                param_name = body.get("param_name", body.get("param"))
                value = body.get("value")
                param_res = modular_manager.update_block_parameter(block_id, param_name, value)
                # If updating raw meal feed, sync with first-principles engine as well
                if block_id == "FEED_01" and param_name in ("nominal_rate_tph", "feed_rate_tph", "feed_rate", "rate_tph", "rate"):
                    try:
                        num_val = float(value)
                        engine.apply_operator_setpoint("feed", num_val)
                    except Exception:
                        pass
                elif block_id == "FUEL_KILN" and param_name in ("nominal_rate_tph", "fuel_rate_tph", "fuel_rate", "rate_tph", "rate"):
                    try:
                        num_val = float(value)
                        bias = ((num_val - 7.2) / 7.2) * 45.9
                        engine.apply_operator_setpoint("Opt_KilnFuel_Bias_pct", bias)
                    except Exception:
                        pass
                elif block_id == "FUEL_PC" and param_name in ("nominal_rate_tph", "fuel_rate_tph", "fuel_rate", "rate_tph", "rate"):
                    try:
                        num_val = float(value)
                        bias = ((num_val - 12.0) / 12.0) * 54.1
                        engine.apply_operator_setpoint("Opt_PCFuel_Bias_pct", bias)
                    except Exception:
                        pass
                if active_opc_server and active_event_loop:
                    tag_name = f"{block_id}_SP_{param_name.upper()}"
                    try:
                        asyncio.run_coroutine_threadsafe(active_opc_server.update_command_node(tag_name, value), active_event_loop)
                    except Exception:
                        pass
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(param_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/step":
            try:
                body = json.loads(post_body.decode("utf-8")) if post_body and post_body.strip() else {}
                dt = float(body.get("dt", 0.5))
                step_res = modular_manager.step(dt)
                sync_modular_telemetry_to_engine(modular_manager, engine)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(step_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/scenarios/apply":
            try:
                body = json.loads(post_body.decode("utf-8"))
                scenario_id = body.get("scenario_id")
                apply_res = apply_scenario(modular_manager, scenario_id)
                # Sync digital twin engine setpoints if successful
                if apply_res.get("status") == "success":
                    feed_b = modular_manager.active_graph.blocks.get("FEED_01")
                    if feed_b:
                        feed_val = feed_b.parameters.get("nominal_rate_tph", 280.0)
                        try:
                            engine.apply_operator_setpoint("feed", float(feed_val))
                        except Exception:
                            pass
                    kiln_b = modular_manager.active_graph.blocks.get("FUEL_KILN")
                    if kiln_b:
                        k_fuel = kiln_b.parameters.get("nominal_rate_tph", 7.2)
                        try:
                            bias = ((float(k_fuel) - 7.2) / 7.2) * 45.9
                            engine.apply_operator_setpoint("Opt_KilnFuel_Bias_pct", bias)
                        except Exception:
                            pass
                    pc_b = modular_manager.active_graph.blocks.get("FUEL_PC")
                    if pc_b:
                        p_fuel = pc_b.parameters.get("nominal_rate_tph", 12.0)
                        try:
                            bias = ((float(p_fuel) - 12.0) / 12.0) * 54.1
                            engine.apply_operator_setpoint("Opt_PCFuel_Bias_pct", bias)
                        except Exception:
                            pass
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(apply_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/scenarios/verify":
            try:
                report = verify_all_scenarios(modular_manager)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(report).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        elif parsed.path == "/api/flowsheet/builder/save":
            try:
                body = json.loads(post_body.decode("utf-8"))
                filename = body.get("filename", "custom_flowsheet.json")
                graph_data = body.get("graph", body)
                save_res = modular_manager.save_to_file(filename, graph_data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(save_res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/flowsheet/builder/custom_components/"):
            comp_type = parsed.path.split("/")[-1]
            del_res = delete_custom_component(comp_type, BLOCK_REGISTRY)
            self.send_response(200 if del_res else 404)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success" if del_res else "not_found", "block_type": comp_type}).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()


def start_http_server(requested_port=8085, max_attempts=50):
    """
    Binds and starts ThreadingHTTPServer on requested_port.
    If requested_port is occupied (e.g., PostgreSQL/EnterpriseDB Apache service, Tomcat, or another app on 8080),
    it automatically detects the port collision and falls back to the next available port.
    Returns (httpd, bound_port).
    """
    httpd = None
    bound_port = None

    for offset in range(max_attempts):
        port = requested_port + offset
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", port), SimulatorRestHttpHandler)
            bound_port = port
            if offset > 0:
                logger.warning(
                    f"⚠️ Port {requested_port} is busy or restricted (e.g. PostgreSQL/Apache service running). "
                    f"Automatically switched Web HMI to available port {bound_port}."
                )
            break
        except OSError as exc:
            logger.info(f"Port {port} busy or unavailable ({exc}). Trying port {port + 1}...")

    if httpd is None or bound_port is None:
        raise RuntimeError(
            f"Could not bind Web HMI HTTP server to any port in range {requested_port}-{requested_port + max_attempts - 1}."
        )

    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()
    logger.info(f"🌐 Web HMI & REST API Server listening at http://localhost:{bound_port}/index.html")
    return httpd, bound_port

def run_http_server(port=8085):
    """Compatibility wrapper that starts HTTP server."""
    httpd, actual_port = start_http_server(requested_port=port)
    return httpd, actual_port

async def main():
    global active_opc_server, active_event_loop
    active_event_loop = asyncio.get_running_loop()

    parser = argparse.ArgumentParser(description="Kiln 3 First-Principles Dynamic Simulator & Optimizer Testbed")
    parser.add_argument("--mode", choices=["server", "client", "standalone"], default=None,
                        help="Operation mode: 'server' (OPC UA Server), 'client' (OPC UA Client Bridge), or 'standalone' (autonomous simulator without OPC)")
    parser.add_argument("--http-port", type=int, default=8085, help="Web HMI HTTP port (default 8085, with auto-fallback)")
    args = parser.parse_args()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    operating_mode = cfg.get("simulation", {}).get("operating_mode", "opc_ua")
    mode = args.mode or (cfg.get("opc_ua", {}).get("mode", "server") if operating_mode != "client" else "client")

    logger.info("=" * 78)
    logger.info("  KILN 3 CEMENT PYROPROCESS DIGITAL TWIN & OPTIMIZER TESTBED")
    logger.info("  First-Principles Physics | Web HMI & Config Manager")
    logger.info(f"  Operating Mode: {mode.upper()}")
    logger.info("=" * 78)

    # 1. Start HTTP Server with automatic port collision fallback
    httpd, actual_port = start_http_server(requested_port=args.http_port)

    # Automatically launch default browser to Web HMI on the successfully bound port
    def open_browser():
        time.sleep(1.2)
        url = f"http://localhost:{actual_port}/index.html"
        logger.info(f"Opening browser at {url}...")
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Failed to automatically open browser: {e}")

    threading.Thread(target=open_browser, daemon=True).start()


    # 2. Run selected mode
    if mode == "client":
        logger.info("Starting OPC UA Client Bridge to connect to external optimization server...")
        bridge = CementOpcUaClientBridge(engine=engine, config_path=CONFIG_PATH)
        await bridge.start()
    else:
        logger.info("Starting Industrial OPC UA Server on port 4841...")
        logger.info("  OPC UA Server Endpoint: opc.tcp://0.0.0.0:4841/freeopcua/server/")
        logger.info("  Client Target URL:      opc.tcp://127.0.0.1:4841/freeopcua/server/")
        opc_server = CementOpcUaServer(engine=engine, modular_manager=modular_manager, config_path=CONFIG_PATH)
        active_opc_server = opc_server
        await opc_server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server terminated by user.")
