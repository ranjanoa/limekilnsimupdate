"""
Standard Process Timer (IEC 61131-3).
Supports:
- TON (On-Delay Timer): Output Q turns ON after input IN remains ON for delay time PT.
- TOF (Off-Delay Timer): Output Q remains ON for delay time PT after input IN turns OFF.
- TP (Pulse Timer): Output Q pulses ON for exact duration PT upon rising edge of IN.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class TimerDelay(BlockBase):
    """
    Standard Process Timer (IEC 61131-3).
    Supports:
    - TON (On-Delay Timer): Output Q turns ON after input IN remains ON for delay time PT.
    - TOF (Off-Delay Timer): Output Q remains ON for delay time PT after input IN turns OFF.
    - TP (Pulse Timer): Output Q pulses ON for exact duration PT upon rising edge of IN.
    """
    block_type = "TimerDelay"
    category = "Control / Binary"
    icon = "⏱️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_trigger", PortDirection.IN, StreamPhase.BINARY, "Timer Input Trigger (IN)", required=True),
            Port("out_q", PortDirection.OUT, StreamPhase.BINARY, "Timer State Output (Q)", required=True),
            Port("out_elapsed", PortDirection.OUT, StreamPhase.SIGNAL, "Elapsed Time ET (seconds)", required=False),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "timer_type": {"type": str, "default": "TON", "label": "Timer Mode (TON/TOF/TP)"},
            "preset_time_s": {"type": float, "default": 5.0, "min": 0.01, "max": 3600.0, "unit": "s", "label": "Preset Delay Time (PT)"},
        }

    def initialize(self):
        self.elapsed_time = 0.0
        self.q = False
        self.prev_in = False
        self.state = {
            "input_in": False,
            "output_q": False,
            "elapsed_time_s": 0.0,
            "preset_time_s": 5.0,
            "timing_active": False,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_trigger")
        out_q = outlet_streams.get("out_q")
        out_et = outlet_streams.get("out_elapsed")

        trig = in_s.binary_state if in_s else False
        mode = str(self.parameters.get("timer_type", "TON")).upper()
        pt = float(self.parameters.get("preset_time_s", 5.0))

        # At steady state, timers are considered expired/settled
        if mode == "TON":
            self.q = trig
            self.elapsed_time = pt if trig else 0.0
        elif mode == "TOF":
            self.q = trig
            self.elapsed_time = 0.0
        else:
            # TP
            self.q = False
            self.elapsed_time = 0.0

        self.state["input_in"] = trig
        self.state["output_q"] = self.q
        self.state["elapsed_time_s"] = round(self.elapsed_time, 2)
        self.state["preset_time_s"] = round(pt, 2)
        self.state["timing_active"] = False

        if out_q:
            out_q.update_state(binary_state=self.q, signal_value=1.0 if self.q else 0.0)
        if out_et:
            out_et.update_state(signal_value=self.elapsed_time, temperature_c=self.elapsed_time, mass_flow_tph=0.0)

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        in_s = inlet_streams.get("in_trigger")
        out_q = outlet_streams.get("out_q")
        out_et = outlet_streams.get("out_elapsed")

        trig = in_s.binary_state if in_s else False
        mode = str(self.parameters.get("timer_type", "TON")).upper()
        pt = max(0.01, float(self.parameters.get("preset_time_s", 5.0)))
        timing = False

        if mode == "TON":
            if trig:
                if self.elapsed_time < pt:
                    self.elapsed_time = min(pt, self.elapsed_time + dt)
                    timing = True
                self.q = (self.elapsed_time >= pt)
            else:
                self.elapsed_time = 0.0
                self.q = False

        elif mode == "TOF":
            if trig:
                self.q = True
                self.elapsed_time = 0.0
            else:
                if self.q and self.elapsed_time < pt:
                    self.elapsed_time = min(pt, self.elapsed_time + dt)
                    timing = True
                    self.q = (self.elapsed_time < pt)
                else:
                    self.q = False

        elif mode == "TP":
            rising_edge = trig and not self.prev_in
            if rising_edge and not self.q:
                self.q = True
                self.elapsed_time = 0.0
                timing = True
            elif self.q:
                if self.elapsed_time < pt:
                    self.elapsed_time = min(pt, self.elapsed_time + dt)
                    timing = True
                else:
                    self.q = False

        self.prev_in = trig
        self.state["input_in"] = trig
        self.state["output_q"] = self.q
        self.state["elapsed_time_s"] = round(self.elapsed_time, 2)
        self.state["preset_time_s"] = round(pt, 2)
        self.state["timing_active"] = timing

        if out_q:
            out_q.update_state(binary_state=self.q, signal_value=1.0 if self.q else 0.0)
        if out_et:
            out_et.update_state(signal_value=self.elapsed_time, temperature_c=self.elapsed_time, mass_flow_tph=0.0)
