"""
EXAMPLE EXTERNAL OPTIMIZATION CLIENT (OPC UA)
Demonstrates how an external AI / MPC / APC Optimization Solution connects to the
Cement Plant Simulator via OPC UA, reads live telemetry feedback, solves the
cost/quality optimization problem, and writes optimal supervisory setpoints.

Objective:
- Maximize throughput (increase feed from 280 to 295 tph safely)
- Keep Clinker Free Lime strictly inside 1.10% - 1.35% target quality window
- Minimize specific thermal heat consumption (kcal/kg clinker)
- Balance excess oxygen via Tertiary Air Damper
"""

import asyncio
import logging
import sys
from asyncua import Client, ua

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OPTIMIZER] %(message)s")
logger = logging.getLogger("OptimizerClient")

SERVER_URL = "opc.tcp://127.0.0.1:4841/freeopcua/server/"
NAMESPACE_URI = "http://cement.simulation.siemens.com/kiln3/"

async def run_optimizer():
    logger.info(f"Connecting to Cement Simulator OPC UA Server at: {SERVER_URL}...")
    
    async with Client(url=SERVER_URL) as client:
        logger.info("✓ Connected to OPC UA Server successfully!")
        
        idx = await client.get_namespace_index(NAMESPACE_URI)
        objects = client.nodes.objects

        # Resolve Node References in Address Space
        # Feedback Nodes
        node_feed = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:K3F07_FeedRate_tph"])
        node_clinker = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:ClinkerProduction_tph"])
        node_heat_cons = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:SpecificHeat_kcal_kg"])
        node_pc_temp = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:K3T62A_PrecalcinerTemp_C"])
        node_sinter = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:TERMO_SinteringTemp_C"])
        node_free_lime = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:CalLivre_FreeLime_pct"])
        node_o2 = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Feedback", f"{idx}:K3Q01_KilnInletO2_pct"])

        # Command Nodes
        node_opt_enable = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_Enable"])
        node_opt_feed_sp = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_FeedRate_SP"])
        node_opt_pc_sp = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_PCTemp_SP"])
        node_opt_sinter_sp = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_SinteringTemp_SP"])
        node_opt_kiln_bias = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_KilnFuel_Bias_pct"])
        node_opt_tad_sp = await objects.get_child([f"{idx}:CementPlant_Kiln3", f"{idx}:Commands", f"{idx}:Opt_TADDamper_SP"])

        # 1. Enable External Optimizer Authority in Simulator
        await node_opt_enable.write_value(True, ua.VariantType.Boolean)
        logger.info(">>> TAKEOVER: Opt_Enable set to TRUE. External Optimizer has supervisory control.")

        # Optimizer State
        current_feed_target = 280.0
        max_feed_target = 295.0 # Objective: push feed up to 295 tph
        cycle = 0

        logger.info("-----------------------------------------------------------------------------------------")
        logger.info(f"{'Cycle':>5} | {'Feed':>7} | {'Clinker':>7} | {'Sinter':>7} | {'PC Temp':>7} | {'FreeLime':>8} | {'HeatCons':>8} | Action")
        logger.info("-----------------------------------------------------------------------------------------")

        while True:
            cycle += 1
            # 2. Read Plant Feedback
            feed_pv = await node_feed.read_value()
            clinker_pv = await node_clinker.read_value()
            heat_pv = await node_heat_cons.read_value()
            pc_temp_pv = await node_pc_temp.read_value()
            sinter_pv = await node_sinter.read_value()
            free_lime_pv = await node_free_lime.read_value()
            o2_pv = await node_o2.read_value()

            action_desc = "Hold steady"
            kiln_fuel_bias = 0.0

            # 3. Optimization Logic (Constraint Handling & Quality Regulation)
            # Check 1: Is Free Lime within target quality band [1.10% - 1.35%]?
            if free_lime_pv > 1.35:
                # Underburnt clinker: boost sintering temperature & fuel bias
                action_desc = "Free lime high -> Bump kiln fuel bias +1.5%"
                kiln_fuel_bias = +1.5
                await node_opt_sinter_sp.write_value(1460.0, ua.VariantType.Float)
            elif free_lime_pv < 1.10:
                # Overburnt clinker: reduce fuel to save energy
                action_desc = "Free lime low (overburnt) -> Trim kiln fuel -1.0%"
                kiln_fuel_bias = -1.0
                await node_opt_sinter_sp.write_value(1445.0, ua.VariantType.Float)
            else:
                # Quality is in ideal sweet spot (1.10% - 1.35%):
                # If stable, push production throughput up towards 295 tph!
                if current_feed_target < max_feed_target:
                    current_feed_target = min(max_feed_target, current_feed_target + 1.5)
                    action_desc = f"Quality OK -> Ramp feed target to {current_feed_target:.1f} tph"
                else:
                    action_desc = f"Optimal production target ({current_feed_target:.1f} tph) reached & held"

            # Check 2: Oxygen balance
            tad_sp = 99.0
            if o2_pv < 2.0:
                tad_sp = 100.0 # open TAD to supply more combustion air
            elif o2_pv > 3.0:
                tad_sp = 95.0  # throttle TAD to reduce excess draft heat losses

            # 4. Write Optimized Setpoints to OPC UA Server
            await node_opt_feed_sp.write_value(float(current_feed_target), ua.VariantType.Float)
            await node_opt_kiln_bias.write_value(float(kiln_fuel_bias), ua.VariantType.Float)
            await node_opt_tad_sp.write_value(float(tad_sp), ua.VariantType.Float)

            logger.info(f"{cycle:>5} | {feed_pv:>6.1f}t | {clinker_pv:>6.1f}t | {sinter_pv:>6.1f}C | {pc_temp_pv:>6.1f}C | {free_lime_pv:>7.2f}% | {heat_pv:>6.1f}kc | {action_desc}")

            await asyncio.sleep(2.0) # Optimizer executes every 2 seconds

if __name__ == "__main__":
    try:
        asyncio.run(run_optimizer())
    except KeyboardInterrupt:
        logger.info("Optimizer client terminated.")
    except Exception as e:
        logger.error(f"Optimizer error: {e}")
