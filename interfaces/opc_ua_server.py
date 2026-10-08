"""
OPC UA SERVER FOR CEMENT PLANT DYNAMIC SIMULATOR
Enables External Optimizers (APC, MPC, AI/RL, Siemens SIMIT, MATLAB)
to Read Process Telemetry and Write Optimal Setpoints in Real Time.
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
    def __init__(self, engine=None, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "plant_config.json")
        self.config_path = config_path

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.engine = engine if engine else FirstPrinciplesEngine(config_path=self.config_path)
        self.server = Server()
        
        opc_cfg = self.cfg.get("opc_ua", {})
        self.endpoint = opc_cfg.get("server_endpoint", "opc.tcp://0.0.0.0:4841/freeopcua/server/")
        self.uri = opc_cfg.get("namespace_uri", "http://cement.simulation.siemens.com/kiln3/")
        self.publish_interval_ms = opc_cfg.get("publish_interval_ms", 500)

        self.feedback_nodes = {}
        self.command_nodes = {}
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
        logger.info(f"Registered OPC UA Namespace: '{self.uri}' with index {idx}")

        # Root Folder for Cement Plant
        objects = self.server.nodes.objects
        self.namespace_idx = idx
        self.plant_folder = await objects.add_folder(idx, "CementPlant_Kiln3")
        self.feedback_folder = await self.plant_folder.add_folder(idx, "Feedback")
        self.commands_folder = await self.plant_folder.add_folder(idx, "Commands")

        tag_dict = self.cfg.get("tag_dictionary", [])
        if tag_dict:
            for tag in tag_dict:
                name = tag["tag_id"]
                category = tag.get("category", "measurement")
                var_type = ua.VariantType.Boolean if tag.get("type") == "Boolean" else ua.VariantType.Float
                default_val = tag.get("default", 0.0)
                if category == "setpoint":
                    node = await self.commands_folder.add_variable(idx, name, default_val, var_type)
                    await node.set_writable()
                    self.command_nodes[name] = node
                else:
                    node = await self.feedback_folder.add_variable(idx, name, default_val, var_type)
                    if tag.get("opc_direction") == "read":
                        await node.set_writable()
                    else:
                        await node.set_read_only()
                    self.feedback_nodes[name] = node
        else:
            # Fallback to legacy specs
            feedback_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("feedback", [])
            for spec in feedback_specs:
                name = spec["name"]
                initial_val = 0.0
                node = await self.feedback_folder.add_variable(idx, name, initial_val, ua.VariantType.Float)
                await node.set_read_only()
                self.feedback_nodes[name] = node

            command_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("commands", [])
            for spec in command_specs:
                name = spec["name"]
                default_val = spec.get("default", 0.0)
                var_type = ua.VariantType.Boolean if spec.get("type") == "Boolean" else ua.VariantType.Float
                node = await self.commands_folder.add_variable(idx, name, default_val, var_type)
                await node.set_writable()
                self.command_nodes[name] = node

        logger.info(f"OPC UA Address Space initialized: {len(self.feedback_nodes)} Feedback nodes, {len(self.command_nodes)} Command nodes.")

    async def register_node(self, tag):
        """Dynamically registers a newly added tag in the OPC UA address space."""
        name = tag["tag_id"]
        category = tag.get("category", "measurement")
        var_type = ua.VariantType.Boolean if tag.get("type") == "Boolean" else ua.VariantType.Float
        default_val = tag.get("default", 0.0)
        idx = self.namespace_idx
        if category == "setpoint":
            if name not in self.command_nodes:
                node = await self.commands_folder.add_variable(idx, name, default_val, var_type)
                await node.set_writable()
                self.command_nodes[name] = node
                logger.info(f"Dynamically registered OPC UA Command node: {name}")
        else:
            if name not in self.feedback_nodes:
                node = await self.feedback_folder.add_variable(idx, name, default_val, var_type)
                if tag.get("opc_direction") == "read":
                    await node.set_writable()
                else:
                    await node.set_read_only()
                self.feedback_nodes[name] = node
                logger.info(f"Dynamically registered OPC UA Feedback node: {name}")

    async def update_command_node(self, loop_or_tag, value):
        """Updates command node value when operator modifies setpoint on Web HMI."""
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
            val = float(value)
            await self.command_nodes[tag_id].write_value(val, ua.VariantType.Float)
            self.current_commands[tag_id] = val

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

                # 1. Read Commands written by External Optimizer
                for cmd_name, node in self.command_nodes.items():
                    val = await node.read_value()
                    self.current_commands[cmd_name] = val

                # 2. Advance First-Principles Physics Step
                self.engine.step(sim_dt, opt_commands=self.current_commands)

                # 3. Publish Telemetry Feedback to OPC UA Nodes periodically
                now = asyncio.get_event_loop().time()
                if now - last_sync_time >= sync_interval:
                    last_sync_time = now
                    telemetry = self.engine.get_telemetry_dict()
                    for node_name, node in self.feedback_nodes.items():
                        if node_name in telemetry:
                            await node.write_value(float(telemetry[node_name]), ua.VariantType.Float)

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
