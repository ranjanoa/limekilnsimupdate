"""
Physical-to-Signal Process Transmitter.
Taps into any physical material or gas stream (SOLID/GAS/AIR/FUEL)
and transmits an analog measurement signal (Temperature, Pressure, Flow) for controllers.
"""

from typing import Dict, List, Any
import copy
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class ProcessTransmitter(BlockBase):
    """
    Physical-to-Signal Process Transmitter.
    Taps into any physical material or gas stream (SOLID/GAS/AIR/FUEL)
    and transmits an analog measurement signal (Temperature, Pressure, Flow) for controllers.
    """
    block_type = "ProcessTransmitter"
    category = "Control / Analog"
    icon = "📡"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_process", PortDirection.IN, StreamPhase.ANY, "Physical process stream to measure", required=True),
            Port("out_process", PortDirection.OUT, StreamPhase.ANY, "Passthrough process stream", required=False),
            Port("out_signal", PortDirection.OUT, StreamPhase.SIGNAL, "Transmitted analog signal output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "variable": {"type": str, "default": "TEMPERATURE", "label": "Measured Variable (TEMPERATURE/PRESSURE/MASS_FLOW/VOLUME_FLOW)"},
            "range_min": {"type": float, "default": 0.0, "label": "Transmitter Range Low (0%)"},
            "range_max": {"type": float, "default": 1200.0, "label": "Transmitter Range High (100%)"},
            "output_format": {"type": str, "default": "EU", "label": "Output Format (EU/PERCENT_0_100/MA_4_20)"},
        }

    def initialize(self):
        self.state = {
            "pv_raw_eu": 0.0,
            "pv_percent": 0.0,
            "output_signal": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_p = inlet_streams.get("in_process")
        out_p = outlet_streams.get("out_process")
        out_sig = outlet_streams.get("out_signal")

        var_type = str(self.parameters.get("variable", "TEMPERATURE")).upper()
        r_min = float(self.parameters.get("range_min", 0.0))
        r_max = float(self.parameters.get("range_max", 1200.0))
        fmt = str(self.parameters.get("output_format", "EU")).upper()

        raw_val = 0.0
        if in_p:
            if var_type == "PRESSURE":
                raw_val = in_p.pressure_mbar
            elif var_type == "MASS_FLOW":
                raw_val = in_p.mass_flow_tph
            elif var_type == "VOLUME_FLOW":
                raw_val = in_p.volume_flow_nm3h or (in_p.mass_flow_tph * 1000.0 / 1.32)
            else:
                raw_val = in_p.temperature_c

        span = max(1e-4, r_max - r_min)
        pct = max(0.0, min(100.0, ((raw_val - r_min) / span) * 100.0))

        if fmt == "PERCENT_0_100":
            out_sig_val = pct
        elif fmt == "MA_4_20":
            out_sig_val = 4.0 + (pct / 100.0) * 16.0
        else:
            out_sig_val = raw_val

        self.state["pv_raw_eu"] = round(raw_val, 2)
        self.state["pv_percent"] = round(pct, 1)
        self.state["output_signal"] = round(out_sig_val, 2)

        # Passthrough physical stream
        if out_p and in_p:
            out_p.update_state(
                mass_flow_tph=in_p.mass_flow_tph,
                temperature_c=in_p.temperature_c,
                pressure_mbar=in_p.pressure_mbar,
                volume_flow_nm3h=in_p.volume_flow_nm3h,
                composition=copy.deepcopy(in_p.composition),
            )

        # Output signal
        if out_sig:
            out_sig.update_state(signal_value=out_sig_val, temperature_c=out_sig_val, mass_flow_tph=0.0)

        return outlet_streams
