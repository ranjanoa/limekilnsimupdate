"""
OPC UA SERVER FOR CEMENT PLANT DYNAMIC SIMULATOR
Enables External Optimizers (APC, MPC, AI/RL, Siemens SIMIT, MATLAB)
to Read Process Telemetry and Write Optimal Setpoints in Real Time.
Synchronizes bidirectional setpoints and telemetry between OPC UA,
First-Principles ODE Engine, and Modular Flowsheet Graph.
"""

import asyncio
import logging
import os
import sys
import json
from asyncua import Server, ua

# Add parent directory to path to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.first_principles_engine import FirstPrinciplesEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OPC_UA_Server")

class CementOpcUaServer:
    def __init__(self, engine=None, modular_manager=None, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "plant_config.json")
        self.config_path = config_path

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.engine = engine if engine else FirstPrinciplesEngine(config_path=self.config_path)
        self.modular_manager = modular_manager
        self.server = Server()
        
        opc_cfg = self.cfg.get("opc_ua", {})
        self.endpoint = opc_cfg.get("server_endpoint", "opc.tcp://0.0.0.0:4841/freeopcua/server/")
        self.uri = opc_cfg.get("namespace_uri", "http://cement.simulation.siemens.com/kiln3/")
        self.publish_interval_ms = opc_cfg.get("publish_interval_ms", 500)

        self.feedback_nodes = {}
        self.command_nodes = {}
        self.last_command_values = {}
        self.current_commands = {
            "Opt_Enable": False,
            "Opt_FeedRate_SP": 280.0,
            "Opt_PCTemp_SP": 907.0,
            "Opt_SinteringTemp_SP": 1450.0,
            "Opt_KilnFuel_Bias_pct": 0.0,
            "Opt_PCFuel_Bias_pct": 0.0,
            "Opt_PHTopDraft_SP": -56.0,
            "Opt_KilnHoodPress_SP": -0.30,
            "Opt_TADDamper_SP": 99.0,
            "Opt_AltFuel_Subst_SP": 41.5
        }
        self.is_running = False

    async def init_server(self):
        """Initializes OPC UA server address space and registers nodes."""
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name("Kiln 3 Cement Pyroprocess Digital Twin (OPC UA)")

        # Register Namespace
        idx = await self.server.register_namespace(self.uri)
        self.namespace_idx = idx
        logger.info(f"Registered OPC UA Namespace: '{self.uri}' with index {idx}")

        # Root Folder for Cement Plant
        objects = self.server.nodes.objects
        self.plant_folder = await objects.add_folder(ua.NodeId("CementPlant_Kiln3", idx), "CementPlant_Kiln3")
        self.feedback_folder = await self.plant_folder.add_folder(ua.NodeId("CementPlant_Kiln3.Feedback", idx), "Feedback")
        self.commands_folder = await self.plant_folder.add_folder(ua.NodeId("CementPlant_Kiln3.Commands", idx), "Commands")

        # 1. Register tags from configuration tag dictionary
        tag_dict = self.cfg.get("tag_dictionary", [])
        if tag_dict:
            for tag in tag_dict:
                await self.register_node(tag)
        else:
            # Fallback to legacy specs if tag_dictionary missing
            feedback_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("feedback", [])
            for spec in feedback_specs:
                name = spec["name"]
                node = await self.feedback_folder.add_variable(ua.NodeId(name, idx), name, 0.0, ua.VariantType.Float)
                await node.set_read_only()
                self.feedback_nodes[name] = node

            command_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("commands", [])
            for spec in command_specs:
                name = spec["name"]
                default_val = spec.get("default", 0.0)
                var_type = ua.VariantType.Boolean if spec.get("type") == "Boolean" else ua.VariantType.Float
                node = await self.commands_folder.add_variable(ua.NodeId(name, idx), name, default_val, var_type)
                await node.set_writable()
                self.command_nodes[name] = node
                self.last_command_values[name] = default_val

        # 2. Register modular flowsheet equipment tags if modular manager is active
        if self.modular_manager and hasattr(self.modular_manager, "get_opc_tags"):
            for m_tag in self.modular_manager.get_opc_tags():
                await self.register_node(m_tag)

        logger.info(f"OPC UA Address Space initialized: {len(self.feedback_nodes)} Feedback nodes, {len(self.command_nodes)} Command nodes.")

    async def register_node(self, tag):
        """Dynamically registers a newly added tag in the OPC UA address space."""
        name = tag["tag_id"]
        category = tag.get("category", "measurement")
        var_type = ua.VariantType.Boolean if tag.get("type") == "Boolean" else ua.VariantType.Float
        default_val = tag.get("value", tag.get("default", 0.0))
        idx = self.namespace_idx

        # Standardize NodeId
        node_id_str = tag.get("opc_node_id") or tag.get("node_id")
        if node_id_str and ";s=" in node_id_str:
            ident = node_id_str.split(";s=", 1)[1]
            node_id_obj = ua.NodeId(ident, idx)
        elif node_id_str and node_id_str.startswith("ns="):
            try:
                node_id_obj = ua.NodeId.from_string(node_id_str)
            except Exception:
                node_id_obj = ua.NodeId(name, idx)
        else:
            node_id_obj = ua.NodeId(name, idx)

        if category == "setpoint":
            if name not in self.command_nodes:
                try:
                    node = await self.commands_folder.add_variable(node_id_obj, name, default_val, var_type)
                    await node.set_writable()
                    self.command_nodes[name] = node
                    self.last_command_values[name] = default_val
                    self.current_commands[name] = default_val
                    logger.info(f"Registered OPC UA Command node: {name} ({node_id_obj})")
                except Exception as ex:
                    logger.debug(f"Command node {name} registration notice: {ex}")
        else:
            if name not in self.feedback_nodes:
                try:
                    node = await self.feedback_folder.add_variable(node_id_obj, name, default_val, var_type)
                    if tag.get("opc_direction") == "read":
                        await node.set_writable()
                    else:
                        await node.set_read_only()
                    self.feedback_nodes[name] = node
                    logger.info(f"Registered OPC UA Feedback node: {name} ({node_id_obj})")
                except Exception as ex:
                    logger.debug(f"Feedback node {name} registration notice: {ex}")

    def apply_command(self, cmd_name, val):
        """
        Applies an incoming setpoint from an external OPC UA client write to the modular
        flowsheet blocks and first-principles physics engine in real time.
        """
        try:
            num_val = float(val) if not isinstance(val, bool) else (1.0 if val else 0.0)
        except (ValueError, TypeError):
            return

        # 1. Modular block setpoint convention: {BLOCK_ID}_SP_{PARAM_NAME}
        if "_SP_" in cmd_name:
            parts = cmd_name.split("_SP_")
            block_id = parts[0]
            param_name = parts[1].lower()

            if self.modular_manager and hasattr(self.modular_manager, "update_block_parameter"):
                matched_bid = block_id
                if hasattr(self.modular_manager, "active_graph") and self.modular_manager.active_graph:
                    for bid in self.modular_manager.active_graph.blocks.keys():
                        if bid.upper() == block_id.upper():
                            matched_bid = bid
                            break
                self.modular_manager.update_block_parameter(matched_bid, param_name, num_val)
                logger.info(f"📥 OPC UA Write applied to Modular Block: '{matched_bid}.{param_name}' = {num_val}")

            # Coupled sync with first-principles physics engine
            if block_id.upper() in ("FEED_01", "LIMEFEED", "RAW_MEAL_FEED", "FEEDER_1") or param_name in (
                "nominal_rate_tph", "feed_rate_tph", "feed_rate", "rate_tph", "rate"
            ):
                self.engine.apply_operator_setpoint("feed", num_val)
                self.engine.raw_meal_feed = num_val
                self.engine.feed_rate = num_val
            elif block_id.upper() in ("FUEL_KILN", "KILN_FUEL"):
                bias = ((num_val - 7.2) / 7.2) * 45.9
                self.engine.apply_operator_setpoint("Opt_KilnFuel_Bias_pct", bias)
            elif block_id.upper() in ("FUEL_PC", "PC_FUEL"):
                bias = ((num_val - 12.0) / 12.0) * 54.1
                self.engine.apply_operator_setpoint("Opt_PCFuel_Bias_pct", bias)

        # 2. Standard kiln optimizer setpoint tags from plant_config.json
        elif cmd_name == "Opt_FeedRate_SP":
            self.engine.apply_operator_setpoint("feed", num_val)
            self.engine.raw_meal_feed = num_val
            self.engine.feed_rate = num_val
            if self.modular_manager and hasattr(self.modular_manager, "active_graph") and self.modular_manager.active_graph:
                for bid, b in self.modular_manager.active_graph.blocks.items():
                    if b.block_type == "GravimetricFeeder":
                        self.modular_manager.update_block_parameter(bid, "nominal_rate_tph", num_val)
        elif cmd_name == "Opt_PCTemp_SP":
            self.engine.apply_operator_setpoint("tic_pc", num_val)
            if self.modular_manager and hasattr(self.modular_manager, "active_graph") and self.modular_manager.active_graph:
                if "CALC_01" in self.modular_manager.active_graph.blocks:
                    self.modular_manager.update_block_parameter("CALC_01", "target_calciner_temp_c", num_val)
        elif cmd_name == "Opt_SinteringTemp_SP":
            self.engine.apply_operator_setpoint("tic_bz", num_val)
        elif cmd_name == "Opt_KilnFuel_Bias_pct":
            self.engine.apply_operator_setpoint("Opt_KilnFuel_Bias_pct", num_val)
        elif cmd_name == "Opt_PCFuel_Bias_pct":
            self.engine.apply_operator_setpoint("Opt_PCFuel_Bias_pct", num_val)
        elif cmd_name == "Opt_PHTopDraft_SP":
            self.engine.apply_operator_setpoint("pic_ph", num_val)
        elif cmd_name == "Opt_KilnHoodPress_SP":
            self.engine.apply_operator_setpoint("pic_kh", num_val)
        elif cmd_name == "Opt_TADDamper_SP":
            self.engine.apply_operator_setpoint("aic_o2", num_val)

    async def update_command_node(self, loop_or_tag, value):
        """Updates command node value when operator modifies setpoint on Web HMI or REST API."""
        mapping = {
            "feed": "Opt_FeedRate_SP",
            "tic_pc": "Opt_PCTemp_SP",
            "tic_bz": "Opt_SinteringTemp_SP",
            "pic_ph": "Opt_PHTopDraft_SP",
            "pic_kh": "Opt_KilnHoodPress_SP",
            "aic_o2": "Opt_TADDamper_SP"
        }
        tag_id = mapping.get(loop_or_tag, loop_or_tag)
        if tag_id in self.command_nodes:
            val = float(value) if not isinstance(value, bool) else (1.0 if value else 0.0)
            await self.command_nodes[tag_id].write_value(val, ua.VariantType.Float)
            self.current_commands[tag_id] = val
            self.last_command_values[tag_id] = val

    async def start(self):
        """Starts OPC UA server and the real-time simulation synchronization loop."""
        await self.init_server()
        await self.server.start()
        self.is_running = True
        logger.info(f"=================================================================")
        logger.info(f"⚡ OPC UA SERVER LISTENING AT: {self.endpoint}")
        logger.info(f"   External Optimizers can connect and write to Commands folder")
        logger.info(f"=================================================================")

        # Run real-time simulation loop
        sim_dt = self.cfg.get("simulation", {}).get("time_step_seconds", 0.1)
        sync_interval = self.publish_interval_ms / 1000.0

        try:
            last_sync_time = asyncio.get_event_loop().time()
            while self.is_running:
                loop_start = asyncio.get_event_loop().time()

                # 1. Read Commands written by External Optimizer / OPC UA Clients
                for cmd_name, node in list(self.command_nodes.items()):
                    try:
                        val = await node.read_value()
                    except Exception:
                        continue

                    self.current_commands[cmd_name] = val
                    prev_val = self.last_command_values.get(cmd_name)

                    if prev_val is None:
                        self.last_command_values[cmd_name] = val
                    elif isinstance(val, bool) or isinstance(prev_val, bool):
                        if val != prev_val:
                            self.last_command_values[cmd_name] = val
                            self.apply_command(cmd_name, val)
                    else:
                        try:
                            if abs(float(val) - float(prev_val)) > 1e-4:
                                self.last_command_values[cmd_name] = val
                                self.apply_command(cmd_name, val)
                        except (ValueError, TypeError):
                            if val != prev_val:
                                self.last_command_values[cmd_name] = val
                                self.apply_command(cmd_name, val)

                # 2. Advance First-Principles Physics & Modular Dynamic Step
                self.engine.step(sim_dt, opt_commands=self.current_commands)
                if self.modular_manager and hasattr(self.modular_manager, "step"):
                    try:
                        self.modular_manager.step(sim_dt)
                    except Exception as step_err:
                        logger.debug(f"Modular manager step tick: {step_err}")

                # 3. Publish Telemetry Feedback to OPC UA Nodes periodically
                now = asyncio.get_event_loop().time()
                if now - last_sync_time >= sync_interval:
                    last_sync_time = now
                    telemetry = self.engine.get_telemetry_dict()

                    # Collect modular block telemetry & measurements
                    modular_telemetry = {}
                    if self.modular_manager and hasattr(self.modular_manager, "get_opc_tags"):
                        for m_tag in self.modular_manager.get_opc_tags():
                            t_id = m_tag.get("tag_id")
                            if t_id:
                                modular_telemetry[t_id] = m_tag.get("live_value", m_tag.get("value", 0.0))
                                if t_id not in self.feedback_nodes and t_id not in self.command_nodes:
                                    try:
                                        await self.register_node(m_tag)
                                    except Exception as reg_err:
                                        logger.debug(f"Dynamic tag reg {t_id}: {reg_err}")

                    for node_name, node in self.feedback_nodes.items():
                        val_to_write = None
                        if node_name in modular_telemetry:
                            val_to_write = modular_telemetry[node_name]
                        elif node_name in telemetry:
                            val_to_write = telemetry[node_name]

                        if val_to_write is not None:
                            try:
                                await node.write_value(float(val_to_write), ua.VariantType.Float)
                            except Exception:
                                pass

                # Sleep to maintain real-time pacing
                elapsed = asyncio.get_event_loop().time() - loop_start
                sleep_time = max(0.001, sim_dt - elapsed)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("OPC UA Server task cancelled.")
        finally:
            await self.stop()

    async def stop(self):
        """Gracefully shuts down OPC UA server."""
        if self.is_running:
            self.is_running = False
            await self.server.stop()
            logger.info("OPC UA Server stopped.")

async def main():
    server = CementOpcUaServer()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
