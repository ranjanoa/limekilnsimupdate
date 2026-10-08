"""
OPC UA CLIENT BRIDGE FOR CEMENT PLANT DYNAMIC SIMULATOR
Enables the simulator to act as an OPC UA CLIENT connected to an external OPC UA Server
(e.g., external optimizer server, DCS gateway, or Aspen/Pavilion/SIMIT server).

Workflow:
1. Connects to the external OPC UA Server at target endpoint.
2. Periodically pushes process feedback/telemetry nodes to the external server.
3. Periodically pulls supervisory optimization commands and setpoints from the external server.
4. Feeds commands into the First-Principles Engine in real time.
"""

import asyncio
import json
import logging
import os
import sys
from asyncua import Client, ua

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.first_principles_engine import FirstPrinciplesEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OPC_CLIENT_BRIDGE] %(message)s")
logger = logging.getLogger("OpcClientBridge")

class CementOpcUaClientBridge:
    def __init__(self, engine=None, config_path=None, server_url=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "plant_config.json")
        self.config_path = config_path

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.engine = engine if engine else FirstPrinciplesEngine(config_path=self.config_path)
        
        opc_cfg = self.cfg.get("opc_ua", {})
        self.server_url = server_url or opc_cfg.get("client_target_endpoint", "opc.tcp://127.0.0.1:4841/freeopcua/server/")
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

    async def connect_and_resolve_nodes(self, client):
        """Resolves feedback and command node handles on the external server."""
        try:
            idx = await client.get_namespace_index(self.uri)
            logger.info(f"Connected to external OPC UA server. Namespace '{self.uri}' index: {idx}")
            objects = client.nodes.objects

            # Feedback nodes to write telemetry to
            feedback_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("feedback", [])
            for spec in feedback_specs:
                name = spec["name"]
                try:
                    node = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:{name}"])
                    self.feedback_nodes[name] = node
                except Exception as ex:
                    logger.warning(f"Could not resolve feedback node '{name}': {ex}")

            # Command nodes to read setpoints from
            command_specs = self.cfg.get("opc_ua", {}).get("nodes", {}).get("commands", [])
            for spec in command_specs:
                name = spec["name"]
                try:
                    node = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:{name}"])
                    self.command_nodes[name] = node
                except Exception as ex:
                    logger.warning(f"Could not resolve command node '{name}': {ex}")

            logger.info(f"Successfully bound {len(self.feedback_nodes)} Feedback nodes and {len(self.command_nodes)} Command nodes.")
            return True
        except Exception as e:
            logger.error(f"Failed to resolve address space on external server: {e}")
            return False

    async def start(self):
        """Main real-time bridge execution loop with automatic reconnection."""
        self.is_running = True
        sim_dt = self.cfg.get("simulation", {}).get("time_step_seconds", 0.1)
        sync_interval = self.publish_interval_ms / 1000.0

        logger.info(f"Starting OPC UA Client Bridge targeting: {self.server_url}")

        while self.is_running:
            try:
                async with Client(url=self.server_url) as client:
                    success = await self.connect_and_resolve_nodes(client)
                    if not success:
                        logger.warning("Retrying connection in 5 seconds...")
                        await asyncio.sleep(5)
                        continue

                    last_sync_time = asyncio.get_event_loop().time()

                    while self.is_running:
                        loop_start = asyncio.get_event_loop().time()

                        # 1. Read Commands from External Server
                        for cmd_name, node in self.command_nodes.items():
                            try:
                                val = await node.read_value()
                                self.current_commands[cmd_name] = val
                            except Exception:
                                pass

                        # 2. Advance First-Principles Physics Step
                        self.engine.step(sim_dt, opt_commands=self.current_commands)

                        # 3. Write Telemetry Feedback to External Server
                        now = asyncio.get_event_loop().time()
                        if now - last_sync_time >= sync_interval:
                            last_sync_time = now
                            telemetry = self.engine.get_telemetry_dict()
                            for node_name, node in self.feedback_nodes.items():
                                if node_name in telemetry:
                                    try:
                                        await node.write_value(float(telemetry[node_name]), ua.VariantType.Float)
                                    except Exception:
                                        pass

                        # Maintain Real-Time Step
                        elapsed = asyncio.get_event_loop().time() - loop_start
                        sleep_time = max(0.001, sim_dt - elapsed)
                        await asyncio.sleep(sleep_time)

            except (ConnectionError, OSError, asyncio.TimeoutError) as e:
                logger.warning(f"Connection lost or could not connect to {self.server_url}: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                logger.info("OPC UA Client Bridge cancelled.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in client bridge: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    def stop(self):
        self.is_running = False
        logger.info("OPC UA Client Bridge stopped.")

async def main():
    bridge = CementOpcUaClientBridge()
    await bridge.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminated by user.")
