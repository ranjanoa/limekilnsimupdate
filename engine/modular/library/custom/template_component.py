"""
=============================================================================
CUSTOM COMPONENT TEMPLATE
=============================================================================
Instructions for adding a custom unit operation to the Flowsheet Simulator:

1. Duplicate this file or create a new `.py` file in this `custom/` directory.
   Example: `biomass_gasifier.py` or `flash_dryer.py`.
2. Change the class name and `block_type` to your component's name.
3. Remove `is_template = True` (or change it to False).
4. Define your connection ports in `_define_ports()`.
   Supported Stream Phases: SOLID, GAS, FUEL, AIR, LIQUID.
   Port Directions: PortDirection.IN, PortDirection.OUT.
5. Declare user parameters in `_define_parameters()` with defaults and ranges.
6. Write your mass & heat balance equations in `evaluate_steady_state()`.
7. (Optional) Implement dynamic holdup integration in `step(dt, ...)`.
8. Save the file!
   THAT'S IT! The simulator automatically discovers and registers your new
   component into the Library Palette without requiring any server restarts!
=============================================================================
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class TemplateComponent(BlockBase):
    """
    Template Component for Custom Unit Operations.
    Copy this class, rename it, implement your physics, and it will be auto-registered!
    """

    # 1. Unique component identifier and UI metadata
    block_type: str = "TemplateComponent"
    category: str = "Custom"  # E.g. "Custom", "Combustion", "Separation", "Cooling", "Pyroprocess"
    icon: str = "⚙️"          # Any emoji or icon code

    # NOTE: Set is_template = False (or delete this attribute) when creating your real block.
    # When is_template = True, this base template class is ignored by the active component palette.
    is_template: bool = True

    def _define_ports(self) -> List[Port]:
        """
        Define input and output connection ports.
        Each port enforces material phase compatibility when wiring in the CAD canvas.
        """
        return [
            Port(
                name="in_feed",
                direction=PortDirection.IN,
                phase=StreamPhase.SOLID,
                description="Raw solid material feed inlet",
                required=True,
            ),
            Port(
                name="in_gas",
                direction=PortDirection.IN,
                phase=StreamPhase.GAS,
                description="Process gas inlet",
                required=False,
            ),
            Port(
                name="out_product",
                direction=PortDirection.OUT,
                phase=StreamPhase.SOLID,
                description="Processed solid product discharge",
                required=True,
            ),
            Port(
                name="out_gas",
                direction=PortDirection.OUT,
                phase=StreamPhase.GAS,
                description="Exhaust gas outlet",
                required=False,
            ),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        Declare parameters that can be adjusted in the Property Inspector or via OPC UA.
        Types supported: float, int, bool, str.
        """
        return {
            "efficiency_pct": {
                "type": float,
                "default": 96.0,
                "min": 10.0,
                "max": 100.0,
                "unit": "%",
                "label": "Process Yield Efficiency",
            },
            "operating_temp_c": {
                "type": float,
                "default": 180.0,
                "min": 20.0,
                "max": 1400.0,
                "unit": "°C",
                "label": "Target Operating Temperature",
            },
            "pressure_loss_mbar": {
                "type": float,
                "default": 8.5,
                "min": 0.0,
                "max": 50.0,
                "unit": "mbar",
                "label": "Gas Draft Drop (ΔP)",
            },
            "ambient_heat_loss_pct": {
                "type": float,
                "default": 2.0,
                "min": 0.0,
                "max": 15.0,
                "unit": "%",
                "label": "Shell Thermal Loss",
            },
        }

    def initialize(self):
        """
        Initialize internal states, dynamic variables, and telemetry readouts.
        These appear directly in HMI cards and are published as live OPC UA tags.
        """
        self.state = {
            "product_rate_tph": 100.0,
            "product_temp_c": 180.0,
            "gas_outlet_nm3h": 0.0,
            "heat_loss_gjh": 0.5,
            "recovery_yield_pct": 96.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        """
        Solve algebraic steady-state equations for mass, energy, and species.
        
        Args:
            inlet_streams: Dictionary of connected incoming streams keyed by port name.
            outlet_streams: Dictionary of connected outgoing streams to be updated.
            
        Returns:
            Updated outlet_streams dictionary.
        """
        in_feed = inlet_streams.get("in_feed")
        in_gas = inlet_streams.get("in_gas")
        out_prod = outlet_streams.get("out_product")
        out_gas = outlet_streams.get("out_gas")

        # 1. Retrieve inlet flow and temperature with fallback values
        m_feed = in_feed.mass_flow_tph if in_feed else 100.0
        t_feed = in_feed.temperature_c if in_feed else 25.0
        p_feed = in_feed.pressure_mbar if in_feed else 0.0

        # 2. Retrieve user parameters
        eff = float(self.parameters.get("efficiency_pct", 96.0)) / 100.0
        target_temp = float(self.parameters.get("operating_temp_c", 180.0))
        dp = float(self.parameters.get("pressure_loss_mbar", 8.5))
        loss_pct = float(self.parameters.get("ambient_heat_loss_pct", 2.0)) / 100.0

        # 3. Calculate process transformations
        m_product = m_feed * eff
        loss_mass = m_feed * (1.0 - eff)

        h_feed = in_feed.enthalpy_gjh if in_feed else (m_feed * 0.95 * t_feed / 1000.0)
        h_loss = h_feed * loss_pct

        # 4. Update unit internal telemetry states
        self.state["product_rate_tph"] = round(m_product, 2)
        self.state["product_temp_c"] = round(target_temp, 1)
        self.state["heat_loss_gjh"] = round(h_loss, 3)
        self.state["recovery_yield_pct"] = round(eff * 100.0, 1)

        # 5. Propagate states to connected outlet streams
        if out_prod:
            out_prod.update_state(
                mass_flow_tph=m_product,
                temperature_c=target_temp,
                pressure_mbar=p_feed,
                composition=copy.deepcopy(in_feed.composition) if in_feed else {},
            )

        if out_gas and in_gas:
            m_gas = in_gas.mass_flow_tph + loss_mass
            out_gas.update_state(
                mass_flow_tph=m_gas,
                temperature_c=target_temp - 10.0,
                pressure_mbar=in_gas.pressure_mbar - dp,
                composition=copy.deepcopy(in_gas.composition),
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """
        Advance dynamic state transitions over timestep dt (seconds).
        By default, delegates to evaluate_steady_state unless you add dynamic holdups.
        """
        self.evaluate_steady_state(inlet_streams, outlet_streams)
