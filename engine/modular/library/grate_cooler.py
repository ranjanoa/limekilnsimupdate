"""
GrateCooler: Reciprocating grate clinker cooler modeling cross-flow heat recuperation,
air split (secondary, tertiary, and vent exhaust air), and clinker nodule cooling.
"""

from typing import Dict, List, Any

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class GrateCooler(BlockBase):
    """
    Reciprocating Hydraulic Grate Clinker Cooler.
    Recovers sensible thermal energy from white-hot clinker (1450°C) into secondary air
    for the kiln burner and tertiary air for the precalciner.
    """
    block_type = "GrateCooler"
    category = "Cooling"
    icon = "cooler"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_clinker_hot", PortDirection.IN, StreamPhase.SOLID, "Hot clinker discharging from rotary kiln", required=True),
            Port("in_cooling_air", PortDirection.IN, StreamPhase.AIR, "Ambient cooling air from under-grate fans", required=False),
            Port("out_clinker_cool", PortDirection.OUT, StreamPhase.SOLID, "Cooled clinker discharged to pan conveyor & silo", required=True),
            Port("out_secondary_air", PortDirection.OUT, StreamPhase.AIR, "Hot secondary combustion air to kiln burner", required=True),
            Port("out_tertiary_air", PortDirection.OUT, StreamPhase.AIR, "Hot tertiary combustion air to precalciner", required=True),
            Port("out_vent_air", PortDirection.OUT, StreamPhase.AIR, "Excess cooling air to cooler baghouse filter", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "grate_area_m2": {"type": float, "default": 105.0, "min": 30.0, "max": 250.0, "unit": "m²", "label": "Grate Active Surface Area"},
            "cooling_air_total_tph": {"type": float, "default": 348.5, "min": 50.0, "max": 600.0, "unit": "t/h", "label": "Nominal Under-grate Air"},
            "secondary_air_split_pct": {"type": float, "default": 24.2, "min": 10.0, "max": 40.0, "unit": "%", "label": "Secondary Air Split"},
            "tertiary_air_split_pct": {"type": float, "default": 36.8, "min": 15.0, "max": 50.0, "unit": "%", "label": "Tertiary Air Split"},
            "recuperation_efficiency": {"type": float, "default": 0.74, "min": 0.50, "max": 0.85, "unit": "-", "label": "Thermal Recuperation Efficiency"},
            "clinker_target_temp_c": {"type": float, "default": 95.0, "min": 60.0, "max": 180.0, "unit": "°C", "label": "Discharge Clinker Temperature"},
        }

    def initialize(self):
        self.state = {
            "secondary_air_temp_c": 1020.0,
            "tertiary_air_temp_c": 880.0,
            "cooler_vent_temp_c": 260.0,
            "clinker_exit_temp_c": 95.0,
            "recuperated_heat_gjh": 205.4,
            "cooler_hydraulic_press_bar": 92.0,
            "heat_loss_gjh": 8.5,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_clinker = inlet_streams.get("in_clinker_hot")
        in_air = inlet_streams.get("in_cooling_air")

        m_clinker = in_clinker.mass_flow_tph if in_clinker else 175.0
        t_clinker_in = in_clinker.temperature_c if in_clinker else 1420.0

        # Under-grate cooling air flow
        if in_air and in_air.mass_flow_tph > 0.0:
            m_air_total = in_air.mass_flow_tph
            t_air_ambient = in_air.temperature_c
        else:
            m_air_total = float(self.parameters.get("cooling_air_total_tph", 348.5))
            t_air_ambient = 25.0

        sec_split = float(self.parameters.get("secondary_air_split_pct", 24.2)) / 100.0
        tert_split = float(self.parameters.get("tertiary_air_split_pct", 36.8)) / 100.0
        vent_split = max(0.0, 1.0 - (sec_split + tert_split))

        m_sec_air = m_air_total * sec_split
        m_tert_air = m_air_total * tert_split
        m_vent_air = m_air_total * vent_split

        eta_recup = float(self.parameters.get("recuperation_efficiency", 0.74))
        target_t = float(self.parameters.get("clinker_target_temp_c", 95.0))
        # Physical aeration dependency: nominal air is ~348.5 t/h. If under-aerated, clinker cannot cool completely
        air_ratio = min(1.5, max(0.2, m_air_total / 348.5))
        t_clinker_exit = target_t + max(0.0, (1.0 - air_ratio) * 160.0)

        # Total heat released by clinker (Cp ~ 0.26 kcal/kg*C)
        cp_clinker = 0.26 * 4.184 / 1000.0  # GJ/(t*C)
        q_clinker_released = m_clinker * cp_clinker * max(0.0, t_clinker_in - t_clinker_exit)

        q_recup = q_clinker_released * eta_recup
        q_loss = q_clinker_released * 0.04

        # Heat partition based on clinker enthalpy recuperation
        # Grate 1 recuperation zone heats secondary air to kiln hood (~1000-1050C)
        # Tertiary air takeoff hood sits immediately adjacent over Grate 1 (~860-880C)
        # Quench grate vent air exhausts to dedusting filter (~240-270C)
        cp_air = 0.26 * 4.184 / 1000.0  # GJ/(t*C)
        # Nominal clinker heat recuperation ~ 185 GJ/h
        t_sec = 25.0 + (q_recup * 0.46) / max(0.01, m_sec_air * cp_air)
        t_sec = max(300.0, min(1250.0, t_sec))

        t_tert = 25.0 + (t_sec - 25.0) * 0.86
        t_tert = max(250.0, min(1050.0, t_tert))

        t_vent = 25.0 + (q_recup * 0.17) / max(0.01, m_vent_air * cp_air)
        t_vent = max(100.0, min(450.0, t_vent))

        # Update block state
        self.state["secondary_air_temp_c"] = round(t_sec, 1)
        self.state["tertiary_air_temp_c"] = round(t_tert, 1)
        self.state["cooler_vent_temp_c"] = round(t_vent, 1)
        self.state["clinker_exit_temp_c"] = round(t_clinker_exit, 1)
        self.state["recuperated_heat_gjh"] = round(q_recup, 2)
        self.state["heat_loss_gjh"] = round(q_loss, 2)

        # Update outlet streams
        out_clinker = outlet_streams.get("out_clinker_cool")
        if out_clinker:
            comp_clinker = in_clinker.composition if in_clinker else {}
            out_clinker.update_state(
                mass_flow_tph=m_clinker,
                temperature_c=t_clinker_exit,
                pressure_mbar=0.0,
                composition=comp_clinker,
            )

        out_sec = outlet_streams.get("out_secondary_air")
        if out_sec:
            out_sec.update_state(
                mass_flow_tph=m_sec_air,
                temperature_c=t_sec,
                pressure_mbar=-0.5,
                composition={"O2_pct": 20.9, "N2_pct": 79.1},
            )

        out_tert = outlet_streams.get("out_tertiary_air")
        if out_tert:
            out_tert.update_state(
                mass_flow_tph=m_tert_air,
                temperature_c=t_tert,
                pressure_mbar=-5.0,
                composition={"O2_pct": 20.9, "N2_pct": 79.1},
            )

        out_vent = outlet_streams.get("out_vent_air")
        if out_vent:
            out_vent.update_state(
                mass_flow_tph=m_vent_air,
                temperature_c=t_vent,
                pressure_mbar=0.0,
                composition={"O2_pct": 20.9, "N2_pct": 79.1},
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic ODE step integrating clinker grate bed thermal inertia."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
        t_sec_tgt = self.state["secondary_air_temp_c"]
        t_tert_tgt = self.state["tertiary_air_temp_c"]

        curr_sec = self.state.get("dynamic_sec_temp_c", t_sec_tgt)
        curr_tert = self.state.get("dynamic_tert_temp_c", t_tert_tgt)

        tau_cooler = 30.0  # seconds

        new_sec = curr_sec + (t_sec_tgt - curr_sec) * (dt / max(0.1, tau_cooler))
        new_tert = curr_tert + (t_tert_tgt - curr_tert) * (dt / max(0.1, tau_cooler))

        self.state["dynamic_sec_temp_c"] = round(new_sec, 1)
        self.state["dynamic_tert_temp_c"] = round(new_tert, 1)
        self.state["secondary_air_temp_c"] = round(new_sec, 1)
        self.state["tertiary_air_temp_c"] = round(new_tert, 1)

        out_sec = outlet_streams.get("out_secondary_air")
        if out_sec:
            out_sec.temperature_c = round(new_sec, 1)
            out_sec.compute_enthalpy()
        out_tert = outlet_streams.get("out_tertiary_air")
        if out_tert:
            out_tert.temperature_c = round(new_tert, 1)
            out_tert.compute_enthalpy()

