"""
Analog 2:1 Multiplexer / Selection Switch Block.
Selects between two analog inputs based on a digital/binary selection signal:
  - When in_select == 0 (False / LOW): Output = in_analog1
  - When in_select == 1 (True / HIGH): Output = in_analog2
Supports optional selection signal inversion and default fallback state.
"""

from typing import Dict, List, Any
from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase


class AnalogSelect(BlockBase):
    """
    Analog 2:1 Multiplexer / Selection Switch Block.
    Selects between two analog inputs based on a digital/binary selection signal:
      - When in_select == 0 (False / LOW): Output = in_analog1
      - When in_select == 1 (True / HIGH): Output = in_analog2
    Supports optional selection signal inversion and default fallback state.
    """
    block_type = "AnalogSelect"
    category = "Control / Analog"
    icon = "🔀"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_analog1", PortDirection.IN, StreamPhase.SIGNAL, "Analog Signal 1 (Selected when Sel=0)", required=False),
            Port("in_analog2", PortDirection.IN, StreamPhase.SIGNAL, "Analog Signal 2 (Selected when Sel=1)", required=False),
            Port("in_select", PortDirection.IN, StreamPhase.ANY, "Digital Selection Connector (0=Analog1, 1=Analog2)", required=False),
            Port("out_selected", PortDirection.OUT, StreamPhase.SIGNAL, "Selected Analog Output", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "default_select": {"type": bool, "default": False, "label": "Default Selection if Unconnected (False=Analog1, True=Analog2)"},
            "invert_select": {"type": bool, "default": False, "label": "Invert Selection Logic (1=Analog1, 0=Analog2)"},
            "description": {"type": str, "default": "Analog 2:1 Selector Switch", "label": "Tag Description"},
        }

    def initialize(self):
        self.state = {
            "analog_1": 0.0,
            "analog_2": 0.0,
            "select_active": False,
            "selected_channel": 1,
            "output_val": 0.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        ia1 = inlet_streams.get("in_analog1")
        ia2 = inlet_streams.get("in_analog2")
        i_sel = inlet_streams.get("in_select")
        out_s = outlet_streams.get("out_selected")

        val1 = ia1.signal_value if ia1 else 0.0
        val2 = ia2.signal_value if ia2 else 0.0

        if i_sel is not None:
            if i_sel.phase == StreamPhase.BINARY:
                sel_active = bool(i_sel.binary_state)
            else:
                sel_active = bool(i_sel.signal_value >= 0.5)
        else:
            sel_active = bool(self.parameters.get("default_select", False))

        if self.parameters.get("invert_select", False):
            sel_active = not sel_active

        if sel_active:
            res = val2
            channel = 2
        else:
            res = val1
            channel = 1

        self.state["analog_1"] = round(val1, 2)
        self.state["analog_2"] = round(val2, 2)
        self.state["select_active"] = sel_active
        self.state["selected_channel"] = channel
        self.state["output_val"] = round(res, 2)

        if out_s:
            out_s.update_state(signal_value=res, temperature_c=res, mass_flow_tph=0.0)
        return outlet_streams
