"""
GasMixer Component Module.
Adiabatic Hot Gas & Flue Gas Mixer (Sum Node).
Blends multiple process gas streams into a single homogeneous gas stream
with conservation of mass, thermal enthalpy, species composition, and dust loading.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class GasMixer(BlockBase):
    """
    Adiabatic Hot Gas & Flue Gas Mixer (Sum Node).
    Blends multiple process gas streams (e.g. Kiln Exhaust Gas, Calciner Exhaust, Cooler Vent Gas, Hot Gas Generator, Infiltration Leakage)
    into a single homogeneous gas stream with rigorous conservation of mass, thermal enthalpy, species composition (CO2%, O2%, N2%, H2O%),
    and dust loading.
    """
    block_type = "GasMixer"
    category = "Flow Control"
    icon = "cloud"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_gas_1", PortDirection.IN, StreamPhase.GAS, "Primary hot gas inlet", required=True),
            Port("in_gas_2", PortDirection.IN, StreamPhase.GAS, "Secondary gas inlet / bypass", required=False),
            Port("in_gas_3", PortDirection.IN, StreamPhase.GAS, "Tertiary gas inlet / leak", required=False),
            Port("in_gas_4", PortDirection.IN, StreamPhase.GAS, "Auxiliary gas inlet", required=False),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Combined hot flue gas discharge", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "pressure_mode": {"type": str, "default": "minimum", "label": "Discharge Pressure Mode"},
        }

    def initialize(self):
        self.state = {
            "total_gas_tph": 0.0,
            "blended_temp_c": 25.0,
            "total_volume_nm3h": 0.0,
            "total_enthalpy_gjh": 0.0,
            "blended_co2_pct": 0.0,
            "blended_o2_pct": 0.0,
            "blended_dust_gm3": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream] = None,
    ) -> Dict[str, ProcessStream]:
        if outlet_streams is None:
            outlet_streams = {}
        if "out_gas" not in outlet_streams:
            outlet_streams["out_gas"] = ProcessStream(
                stream_id=0,
                name=f"{self.block_id}_Blended_Gas",
                phase=StreamPhase.GAS,
                mass_flow_tph=0.0,
                temperature_c=25.0,
            )

        active_inlets = [s for s in inlet_streams.values() if s is not None and s.mass_flow_tph > 0.0]
        out_stream = outlet_streams.get("out_gas")

        if not active_inlets:
            self.state["total_gas_tph"] = 0.0
            self.state["blended_temp_c"] = 25.0
            self.state["total_volume_nm3h"] = 0.0
            self.state["total_enthalpy_gjh"] = 0.0
            self.state["blended_co2_pct"] = 0.0
            self.state["blended_o2_pct"] = 0.0
            self.state["blended_dust_gm3"] = 0.0
            if out_stream:
                out_stream.update_state(mass_flow_tph=0.0, temperature_c=25.0)
            return outlet_streams

        total_mass = sum(s.mass_flow_tph for s in active_inlets)
        total_enthalpy = sum(s.enthalpy_gjh for s in active_inlets)

        # Weighted temperature by mass * Cp
        sum_c_t = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() * s.temperature_c for s in active_inlets)
        sum_c = sum(s.mass_flow_tph * s.get_heat_capacity_kcal_kg_c() for s in active_inlets)
        t_mixed = (sum_c_t / sum_c) if sum_c > 0.0 else 25.0

        p_mixed = min(s.pressure_mbar for s in active_inlets)

        # Weighted species composition
        blended_comp: Dict[str, float] = {}
        for s in active_inlets:
            w = s.mass_flow_tph / total_mass
            comp = s.composition or {"CO2_pct": 20.0, "O2_pct": 3.0, "N2_pct": 70.0, "H2O_pct": 7.0}
            for comp_key, val in comp.items():
                if isinstance(val, (int, float)):
                    blended_comp[comp_key] = blended_comp.get(comp_key, 0.0) + val * w

        # Flue gas density ~1.34 kg/Nm3
        vol_nm3h = (total_mass * 1000.0) / 1.34
        co2_pct = blended_comp.get("CO2_pct", 0.0)
        o2_pct = blended_comp.get("O2_pct", 0.0)
        dust = blended_comp.get("dust_concentration_g_nm3", 0.0)

        self.state["total_gas_tph"] = round(total_mass, 2)
        self.state["blended_temp_c"] = round(t_mixed, 1)
        self.state["total_volume_nm3h"] = round(vol_nm3h, 1)
        self.state["total_enthalpy_gjh"] = round(total_enthalpy, 2)
        self.state["blended_co2_pct"] = round(co2_pct, 2)
        self.state["blended_o2_pct"] = round(o2_pct, 2)
        self.state["blended_dust_gm3"] = round(dust, 2)

        if out_stream:
            out_stream.phase = StreamPhase.GAS
            out_stream.update_state(
                mass_flow_tph=round(total_mass, 3),
                temperature_c=round(t_mixed, 1),
                pressure_mbar=p_mixed,
                composition=blended_comp,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        self.evaluate_steady_state(inlet_streams, outlet_streams)
