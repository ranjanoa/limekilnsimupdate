"""
Custom Component Dynamic Loader & Auto-Registration Engine.
Automatically discovers, validates, and registers user-defined unit operation blocks
from Python source files in the `custom/` directory into BLOCK_REGISTRY.
"""

import os
import sys
import ast
import re
import copy
import inspect
import logging
import importlib.util
from typing import Dict, Type, Any, List, Optional

from ..block_base import BlockBase, Port, PortDirection
from ..stream import ProcessStream, StreamPhase

logger = logging.getLogger("CustomComponentLoader")

CUSTOM_BLOCK_REGISTRY: Dict[str, Type[BlockBase]] = {}


def get_custom_dir() -> str:
    """Returns the absolute directory for custom components."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    custom_dir = os.path.join(base_dir, "custom")
    os.makedirs(custom_dir, exist_ok=True)
    return custom_dir


def load_module_from_path(module_name: str, file_path: str):
    """Dynamically imports a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_custom_components(block_registry: Optional[Dict[str, Type[BlockBase]]] = None) -> Dict[str, Type[BlockBase]]:
    """
    Scans the custom/ folder for Python files, inspects for BlockBase subclasses,
    and automatically registers them into CUSTOM_BLOCK_REGISTRY and block_registry.
    """
    custom_dir = get_custom_dir()
    discovered = {}

    if not os.path.exists(custom_dir):
        return discovered

    for fname in sorted(os.listdir(custom_dir)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue

        file_path = os.path.join(custom_dir, fname)
        module_name = f"engine.modular.library.custom.{fname[:-3]}"

        try:
            mod = load_module_from_path(module_name, file_path)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    inspect.isclass(attr)
                    and issubclass(attr, BlockBase)
                    and attr is not BlockBase
                ):
                    # Skip if explicitly flagged as an abstract template
                    if getattr(attr, "is_template", False):
                        continue

                    block_type = getattr(attr, "block_type", attr.__name__)
                    # Set custom flag
                    attr.is_custom = True
                    attr._source_file = file_path

                    # Validate by creating a test instance
                    try:
                        test_inst = attr(block_id="test_init")
                        if not test_inst.ports:
                            logger.warning(f"Custom block {block_type} has no ports defined, skipping.")
                            continue
                    except Exception as inst_err:
                        logger.warning(f"Could not instantiate custom block {block_type}: {inst_err}")
                        continue

                    CUSTOM_BLOCK_REGISTRY[block_type] = attr
                    discovered[block_type] = attr
                    if block_registry is not None:
                        block_registry[block_type] = attr

                    logger.info(f"Auto-registered custom component: {block_type} from {fname}")
        except Exception as e:
            logger.warning(f"Error loading custom component module {fname}: {e}")

    return discovered


def validate_component_source(source_code: str) -> Dict[str, Any]:
    """
    Validates Python source code for a custom BlockBase component:
    1. Python AST syntax check
    2. Compilation & sandbox execution
    3. Verification of BlockBase subclassing, ports, and parameter schemas
    4. Execution of a test evaluation
    """
    try:
        # 1. Syntax check
        parsed_ast = ast.parse(source_code)
    except SyntaxError as syn_err:
        return {
            "valid": False,
            "error": f"Syntax Error on line {syn_err.lineno}: {syn_err.msg}",
            "line": syn_err.lineno,
            "offset": syn_err.offset,
        }

    # 2. Compile and exec in temporary namespace
    namespace: Dict[str, Any] = {
        "BlockBase": BlockBase,
        "Port": Port,
        "PortDirection": PortDirection,
        "ProcessStream": ProcessStream,
        "StreamPhase": StreamPhase,
        "copy": copy,
        "Dict": Dict,
        "List": List,
        "Any": Any,
        "Optional": Optional,
    }

    try:
        compiled = compile(parsed_ast, filename="<custom_block_sandbox>", mode="exec")
        exec(compiled, namespace)
    except Exception as exec_err:
        import traceback
        tb = traceback.format_exc()
        return {
            "valid": False,
            "error": f"Runtime compilation error: {str(exec_err)}",
            "traceback": tb,
        }

    # 3. Locate BlockBase subclass
    target_cls = None
    for item in namespace.values():
        if (
            inspect.isclass(item)
            and issubclass(item, BlockBase)
            and item is not BlockBase
        ):
            target_cls = item
            break

    if target_cls is None:
        return {
            "valid": False,
            "error": "No subclass of BlockBase found in code. Please inherit from BlockBase.",
        }

    block_type = getattr(target_cls, "block_type", target_cls.__name__)
    category = getattr(target_cls, "category", "Custom")
    icon = getattr(target_cls, "icon", "⚙️")

    # 4. Instantiate and verify ports & parameters
    try:
        inst = target_cls(block_id="test_validate")
        ports = [p.to_dict() for p in inst.ports.values()]
        if not ports:
            return {
                "valid": False,
                "error": "The component defines zero ports in _define_ports(). At least one port is required.",
            }

        in_ports = [p for p in ports if p["direction"] == "IN"]
        out_ports = [p for p in ports if p["direction"] == "OUT"]

        params = {}
        for p_name, p_def in inst.parameter_schema.items():
            param_copy = dict(p_def)
            if "type" in param_copy and isinstance(param_copy["type"], type):
                param_copy["type"] = param_copy["type"].__name__
            params[p_name] = param_copy

        # 5. Test dummy steady-state run
        inlet_dummy = {}
        for p in in_ports:
            phase = StreamPhase(p["phase"])
            inlet_dummy[p["name"]] = ProcessStream(
                stream_id=901,
                name=f"test_{p['name']}",
                phase=phase,
                mass_flow_tph=100.0,
                temperature_c=200.0,
                pressure_mbar=-5.0,
            )
        outlet_dummy = {}
        for p in out_ports:
            phase = StreamPhase(p["phase"])
            outlet_dummy[p["name"]] = ProcessStream(
                stream_id=902,
                name=f"test_{p['name']}",
                phase=phase,
            )

        inst.evaluate_steady_state(inlet_dummy, outlet_dummy)
        inst.step(1.0, inlet_dummy, outlet_dummy)

    except Exception as test_err:
        import traceback
        tb = traceback.format_exc()
        return {
            "valid": False,
            "error": f"Error during component instantiation / balance test: {str(test_err)}",
            "traceback": tb,
        }

    return {
        "valid": True,
        "block_type": block_type,
        "category": category,
        "icon": icon,
        "ports": ports,
        "in_ports_count": len(in_ports),
        "out_ports_count": len(out_ports),
        "parameters": params,
        "docstring": target_cls.__doc__.strip() if target_cls.__doc__ else "",
    }


def save_and_register_custom_component(
    source_code: str,
    block_registry: Optional[Dict[str, Type[BlockBase]]] = None,
    custom_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates code, writes it to engine/modular/library/custom/<filename>.py,
    dynamically reloads it, and registers the component into BLOCK_REGISTRY.
    """
    val = validate_component_source(source_code)
    if not val.get("valid"):
        return val

    block_type = val["block_type"]
    custom_dir = get_custom_dir()

    if not custom_filename:
        # Convert CamelCase to snake_case filename
        clean_name = re.sub(r'(?<!^)(?=[A-Z])', '_', block_type).lower()
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)
        custom_filename = f"{clean_name}.py"
    elif not custom_filename.endswith(".py"):
        custom_filename = f"{custom_filename}.py"

    file_path = os.path.join(custom_dir, custom_filename)

    # Write file to disk
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    # Reload from path
    module_name = f"engine.modular.library.custom.{os.path.splitext(custom_filename)[0]}"
    try:
        mod = load_module_from_path(module_name, file_path)
        target_cls = None
        for item in mod.__dict__.values():
            if (
                inspect.isclass(item)
                and issubclass(item, BlockBase)
                and item is not BlockBase
                and getattr(item, "block_type", "") == block_type
            ):
                target_cls = item
                break

        if target_cls is None:
            # Fallback to any BlockBase subclass in mod
            for item in mod.__dict__.values():
                if inspect.isclass(item) and issubclass(item, BlockBase) and item is not BlockBase:
                    target_cls = item
                    break

        if target_cls is not None:
            target_cls.is_custom = True
            target_cls._source_file = file_path
            CUSTOM_BLOCK_REGISTRY[block_type] = target_cls
            if block_registry is not None:
                block_registry[block_type] = target_cls

            logger.info(f"Successfully saved and registered custom component '{block_type}' to {file_path}")
            val["file_name"] = custom_filename
            val["file_path"] = file_path
            val["message"] = f"Component '{block_type}' registered successfully!"
            return val
        else:
            return {"valid": False, "error": "Failed to re-import registered class from saved file."}

    except Exception as load_err:
        return {"valid": False, "error": f"Failed to reload saved component: {str(load_err)}"}


def delete_custom_component(
    block_type: str,
    block_registry: Optional[Dict[str, Type[BlockBase]]] = None,
) -> bool:
    """Removes a custom component from disk and unregisters it from registries."""
    cls = CUSTOM_BLOCK_REGISTRY.pop(block_type, None)
    if block_registry is not None and block_type in block_registry:
        block_registry.pop(block_type, None)

    if cls and hasattr(cls, "_source_file"):
        try:
            if os.path.exists(cls._source_file):
                os.remove(cls._source_file)
                logger.info(f"Deleted custom component source file: {cls._source_file}")
                return True
        except Exception as e:
            logger.warning(f"Could not delete custom component file: {e}")

    # Also search by naming convention if _source_file was missing
    custom_dir = get_custom_dir()
    clean_name = re.sub(r'(?<!^)(?=[A-Z])', '_', block_type).lower()
    candidate = os.path.join(custom_dir, f"{clean_name}.py")
    if os.path.exists(candidate):
        try:
            os.remove(candidate)
            return True
        except Exception:
            pass

    return cls is not None


def get_custom_components_list() -> List[Dict[str, Any]]:
    """Returns metadata and source code for all currently registered custom components."""
    results = []
    custom_dir = get_custom_dir()

    for block_type, cls in CUSTOM_BLOCK_REGISTRY.items():
        source_code = ""
        file_name = ""
        source_file = getattr(cls, "_source_file", None)
        if source_file and os.path.exists(source_file):
            file_name = os.path.basename(source_file)
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    source_code = f.read()
            except Exception:
                pass

        try:
            temp_inst = cls(block_id="catalog_meta")
            clean_params = {}
            for p_name, p_def in temp_inst.parameter_schema.items():
                p_copy = dict(p_def)
                if "type" in p_copy and isinstance(p_copy["type"], type):
                    p_copy["type"] = p_copy["type"].__name__
                clean_params[p_name] = p_copy

            results.append({
                "type": block_type,
                "category": cls.category,
                "icon": cls.icon,
                "file_name": file_name,
                "ports": [p.to_dict() for p in temp_inst.ports.values()],
                "parameters": clean_params,
                "source_code": source_code,
                "docstring": cls.__doc__.strip() if cls.__doc__ else "",
            })
        except Exception as e:
            logger.warning(f"Error querying custom component metadata for {block_type}: {e}")

    return results


def get_available_templates() -> List[Dict[str, Any]]:
    """Returns curated starter templates for custom component creation."""
    return [
        {
            "id": "generic_unit",
            "name": "Generic Process Unit",
            "category": "General",
            "icon": "⚙️",
            "description": "Standard 1-inlet, 1-outlet mass and thermal unit operation with yield efficiency and thermal delta.",
            "code": GENERIC_UNIT_TEMPLATE_CODE,
        },
        {
            "id": "continuous_reactor",
            "name": "Continuous Kinetic Reactor",
            "category": "Combustion",
            "icon": "⚡",
            "description": "Continuous reaction vessel with solid and gas feeds, conversion kinetics, heat of reaction, and product splits.",
            "code": REACTOR_TEMPLATE_CODE,
        },
        {
            "id": "heat_exchanger",
            "name": "Heat Exchanger / Recuperator",
            "category": "Cooling",
            "icon": "❄️",
            "description": "2-inlet, 2-outlet counter-flow thermal exchanger using effectiveness-NTU method with draft drop.",
            "code": HEAT_EXCHANGER_TEMPLATE_CODE,
        },
        {
            "id": "cyclone_separator",
            "name": "Gas-Solid Cyclone / Separator",
            "category": "Separation",
            "icon": "🌪",
            "description": "Gas-solid centrifugal separator with capture efficiency curve, dust carryover, and draft loss.",
            "code": SEPARATOR_TEMPLATE_CODE,
        },
        {
            "id": "flow_splitter",
            "name": "Proportional Stream Splitter",
            "category": "Flow Control",
            "icon": "🔱",
            "description": "Splits an incoming stream into two branches based on a tunable split ratio percentage.",
            "code": SPLITTER_TEMPLATE_CODE,
        },
        {
            "id": "minimal_scaffold",
            "name": "Clean Scaffold (Minimal)",
            "category": "Custom",
            "icon": "📦",
            "description": "Clean, lightweight BlockBase boilerplate with essential ports, parameters, and balance methods.",
            "code": MINIMAL_SCAFFOLD_CODE,
        },
    ]


# =============================================================================
# CURATED STARTER TEMPLATES CODE STRINGS
# =============================================================================

GENERIC_UNIT_TEMPLATE_CODE = '''"""
Custom Unit Operation: Generic Process Unit
Models steady-state mass throughput and thermal change with efficiency factor.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class CustomProcessUnit(BlockBase):
    """
    Custom Process Unit Operation.
    Adjust parameters, ports, and equations as needed.
    """
    block_type = "CustomProcessUnit"
    category = "General"
    icon = "⚙️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("inlet", PortDirection.IN, StreamPhase.SOLID, "Process material inlet", required=True),
            Port("outlet", PortDirection.OUT, StreamPhase.SOLID, "Process material outlet", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "mass_yield_pct": {
                "type": float,
                "default": 98.5,
                "min": 10.0,
                "max": 100.0,
                "unit": "%",
                "label": "Mass Yield Recovery",
            },
            "temp_delta_c": {
                "type": float,
                "default": 20.0,
                "min": -500.0,
                "max": 1200.0,
                "unit": "°C",
                "label": "Process Temperature Delta",
            },
            "heat_loss_pct": {
                "type": float,
                "default": 1.5,
                "min": 0.0,
                "max": 20.0,
                "unit": "%",
                "label": "Thermal Loss to Ambient",
            },
        }

    def initialize(self):
        """Initializes internal state variables for HMI cards and OPC UA."""
        self.state = {
            "throughput_tph": 100.0,
            "temp_out_c": 80.0,
            "mass_recovery_pct": 98.5,
            "heat_loss_gjh": 0.5,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("inlet")
        out_s = outlet_streams.get("outlet")

        # Read inlet stream properties (with safe fallbacks)
        m_in = in_s.mass_flow_tph if in_s else 100.0
        t_in = in_s.temperature_c if in_s else 60.0
        p_in = in_s.pressure_mbar if in_s else 0.0

        # Read user-configured parameters
        yield_pct = float(self.parameters.get("mass_yield_pct", 98.5)) / 100.0
        delta_t = float(self.parameters.get("temp_delta_c", 20.0))
        loss_pct = float(self.parameters.get("heat_loss_pct", 1.5)) / 100.0

        # Perform process calculations
        m_out = m_in * yield_pct
        t_out = max(0.0, t_in + delta_t)

        h_in = in_s.enthalpy_gjh if in_s else (m_in * 1.05 * t_in / 1000.0)
        h_loss = h_in * loss_pct

        # Update unit internal telemetry states
        self.state["throughput_tph"] = round(m_out, 2)
        self.state["temp_out_c"] = round(t_out, 1)
        self.state["mass_recovery_pct"] = round(yield_pct * 100.0, 1)
        self.state["heat_loss_gjh"] = round(h_loss, 3)

        # Update connected outlet stream
        if out_s:
            comp = copy.deepcopy(in_s.composition) if in_s else {}
            out_s.update_state(
                mass_flow_tph=m_out,
                temperature_c=t_out,
                pressure_mbar=p_in,
                composition=comp,
            )

        return outlet_streams

    def step(
        self,
        dt: float,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> None:
        """Dynamic step falls back to steady-state evaluation."""
        self.evaluate_steady_state(inlet_streams, outlet_streams)
'''

REACTOR_TEMPLATE_CODE = '''"""
Custom Unit Operation: Continuous Kinetic Reactor
Models reaction conversion, heat release, and dual solid-gas outputs.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class CustomKineticReactor(BlockBase):
    """
    Custom Continuous Reactor.
    Models conversion kinetics, reaction enthalpy, and solid/gas products.
    """
    block_type = "CustomKineticReactor"
    category = "Combustion"
    icon = "⚡"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_feed", PortDirection.IN, StreamPhase.SOLID, "Raw material reactant feed", required=True),
            Port("in_gas", PortDirection.IN, StreamPhase.AIR, "Combustion or sweep air/gas", required=False),
            Port("out_product", PortDirection.OUT, StreamPhase.SOLID, "Discharged solid product", required=True),
            Port("out_gas", PortDirection.OUT, StreamPhase.GAS, "Reactor exhaust offgas", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "target_temp_c": {
                "type": float,
                "default": 900.0,
                "min": 200.0,
                "max": 1600.0,
                "unit": "°C",
                "label": "Reactor Operating Temperature",
            },
            "conversion_rate_pct": {
                "type": float,
                "default": 92.0,
                "min": 10.0,
                "max": 100.0,
                "unit": "%",
                "label": "Reaction Conversion Extent",
            },
            "reaction_heat_release_mw": {
                "type": float,
                "default": 15.0,
                "min": 0.0,
                "max": 150.0,
                "unit": "MW",
                "label": "Heat Release Rate",
            },
            "heat_loss_gjh": {
                "type": float,
                "default": 4.5,
                "min": 0.0,
                "max": 50.0,
                "unit": "GJ/h",
                "label": "Shell Thermal Loss",
            },
        }

    def initialize(self):
        self.state = {
            "bed_temperature_c": 900.0,
            "product_rate_tph": 150.0,
            "gas_discharge_nm3h": 85000.0,
            "conversion_pct": 92.0,
            "heat_loss_gjh": 4.5,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_feed = inlet_streams.get("in_feed")
        in_gas = inlet_streams.get("in_gas")
        out_prod = outlet_streams.get("out_product")
        out_gas = outlet_streams.get("out_gas")

        m_feed = in_feed.mass_flow_tph if in_feed else 180.0
        m_gas = in_gas.mass_flow_tph if in_gas else 120.0
        t_target = float(self.parameters.get("target_temp_c", 900.0))
        conv = float(self.parameters.get("conversion_rate_pct", 92.0)) / 100.0
        q_loss = float(self.parameters.get("heat_loss_gjh", 4.5))

        # Mass conversion: calcination or decomposition producing gas and solid
        gas_generated_tph = m_feed * 0.35 * conv
        solid_out_tph = max(1.0, m_feed - gas_generated_tph)
        total_gas_out_tph = m_gas + gas_generated_tph
        v_gas_nm3h = (total_gas_out_tph * 1000.0) / 1.35

        self.state["bed_temperature_c"] = round(t_target, 1)
        self.state["product_rate_tph"] = round(solid_out_tph, 2)
        self.state["gas_discharge_nm3h"] = round(v_gas_nm3h, 0)
        self.state["conversion_pct"] = round(conv * 100.0, 1)
        self.state["heat_loss_gjh"] = round(q_loss, 2)

        # Update Solid Product Outlet
        if out_prod:
            out_prod.update_state(
                mass_flow_tph=solid_out_tph,
                temperature_c=t_target,
                pressure_mbar=0.0,
                composition={"CaO_pct": 65.0, "SiO2_pct": 21.0, "Fe2O3_pct": 3.5},
            )

        # Update Gas Discharge Outlet
        if out_gas:
            out_gas.update_state(
                mass_flow_tph=total_gas_out_tph,
                volume_flow_nm3h=v_gas_nm3h,
                temperature_c=t_target - 15.0,
                pressure_mbar=-18.0,
                composition={"CO2_pct": 32.0, "O2_pct": 2.5, "N2_pct": 65.5},
            )

        return outlet_streams
'''

HEAT_EXCHANGER_TEMPLATE_CODE = '''"""
Custom Unit Operation: Heat Exchanger / Thermal Recuperator
Models counter-flow thermal exchange between hot and cold streams.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class CustomHeatExchanger(BlockBase):
    """
    Counter-flow Heat Exchanger / Recuperator.
    Transfers thermal energy from hot utility or process stream to cold fluid.
    """
    block_type = "CustomHeatExchanger"
    category = "Cooling"
    icon = "❄️"

    def _define_ports(self) -> List[Port]:
        return [
            Port("hot_in", PortDirection.IN, StreamPhase.GAS, "Hot gas stream inlet", required=True),
            Port("cold_in", PortDirection.IN, StreamPhase.AIR, "Cold air or fluid inlet", required=True),
            Port("hot_out", PortDirection.OUT, StreamPhase.GAS, "Cooled gas outlet", required=True),
            Port("cold_out", PortDirection.OUT, StreamPhase.AIR, "Preheated air or fluid outlet", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "effectiveness_pct": {
                "type": float,
                "default": 75.0,
                "min": 10.0,
                "max": 98.0,
                "unit": "%",
                "label": "Thermal Effectiveness (ε)",
            },
            "pressure_drop_mbar": {
                "type": float,
                "default": 12.0,
                "min": 1.0,
                "max": 50.0,
                "unit": "mbar",
                "label": "Gas Side Pressure Drop",
            },
            "ambient_heat_loss_pct": {
                "type": float,
                "default": 2.0,
                "min": 0.0,
                "max": 15.0,
                "unit": "%",
                "label": "Ambient Shell Heat Loss",
            },
        }

    def initialize(self):
        self.state = {
            "duty_gjh": 28.5,
            "hot_outlet_temp_c": 280.0,
            "cold_outlet_temp_c": 450.0,
            "effectiveness_pct": 75.0,
            "heat_loss_gjh": 0.8,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        hot_in = inlet_streams.get("hot_in")
        cold_in = inlet_streams.get("cold_in")
        hot_out = outlet_streams.get("hot_out")
        cold_out = outlet_streams.get("cold_out")

        m_hot = hot_in.mass_flow_tph if hot_in else 150.0
        t_hot = hot_in.temperature_c if hot_in else 650.0
        m_cold = cold_in.mass_flow_tph if cold_in else 120.0
        t_cold = cold_in.temperature_c if cold_in else 30.0

        eff = float(self.parameters.get("effectiveness_pct", 75.0)) / 100.0
        dp = float(self.parameters.get("pressure_drop_mbar", 12.0))
        loss_pct = float(self.parameters.get("ambient_heat_loss_pct", 2.0)) / 100.0

        # Heat capacity rates (Cp ~ 1.05 kJ/kg.K)
        c_hot = m_hot * 1.05
        c_cold = m_cold * 1.01
        c_min = min(c_hot, c_cold)

        # Maximum possible heat transfer Q_max = C_min * (T_hot_in - T_cold_in)
        q_max_gjh = (c_min * max(0.0, t_hot - t_cold)) / 1000.0 * 3600.0 / 3.6
        q_actual_gjh = eff * q_max_gjh

        # Outlet temperatures
        delta_t_hot = (q_actual_gjh * 1000.0 / max(1e-3, c_hot)) / 1000.0
        delta_t_cold = ((q_actual_gjh * (1.0 - loss_pct)) * 1000.0 / max(1e-3, c_cold)) / 1000.0

        t_hot_out = max(t_cold, t_hot - delta_t_hot)
        t_cold_out = min(t_hot, t_cold + delta_t_cold)
        q_loss = q_actual_gjh * loss_pct

        self.state["duty_gjh"] = round(q_actual_gjh, 2)
        self.state["hot_outlet_temp_c"] = round(t_hot_out, 1)
        self.state["cold_outlet_temp_c"] = round(t_cold_out, 1)
        self.state["effectiveness_pct"] = round(eff * 100.0, 1)
        self.state["heat_loss_gjh"] = round(q_loss, 2)

        if hot_out:
            p_hot = (hot_in.pressure_mbar if hot_in else 0.0) - dp
            hot_out.update_state(
                mass_flow_tph=m_hot,
                temperature_c=t_hot_out,
                pressure_mbar=p_hot,
                composition=copy.deepcopy(hot_in.composition) if hot_in else {},
            )

        if cold_out:
            p_cold = (cold_in.pressure_mbar if cold_in else 0.0) - (dp * 0.5)
            cold_out.update_state(
                mass_flow_tph=m_cold,
                temperature_c=t_cold_out,
                pressure_mbar=p_cold,
                composition=copy.deepcopy(cold_in.composition) if cold_in else {},
            )

        return outlet_streams
'''

SEPARATOR_TEMPLATE_CODE = '''"""
Custom Unit Operation: Gas-Solid Cyclone / Separator
Separates particulate solids from gas stream based on collection efficiency.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class CustomCycloneSeparator(BlockBase):
    """
    Gas-Solid Centrifugal Separator.
    Captures solid dust from gas flow into an underflow stream.
    """
    block_type = "CustomCycloneSeparator"
    category = "Separation"
    icon = "🌪"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_mixture", PortDirection.IN, StreamPhase.GAS, "Dust-laden gas mixture", required=True),
            Port("out_clean_gas", PortDirection.OUT, StreamPhase.GAS, "Clean gas top discharge", required=True),
            Port("out_dust", PortDirection.OUT, StreamPhase.SOLID, "Separated dust dipleg underflow", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "collection_efficiency_pct": {
                "type": float,
                "default": 94.0,
                "min": 50.0,
                "max": 99.9,
                "unit": "%",
                "label": "Collection Efficiency (η)",
            },
            "pressure_drop_mbar": {
                "type": float,
                "default": 14.5,
                "min": 2.0,
                "max": 45.0,
                "unit": "mbar",
                "label": "Draft Pressure Drop (ΔP)",
            },
            "solid_loading_kg_nm3": {
                "type": float,
                "default": 0.85,
                "min": 0.05,
                "max": 5.0,
                "unit": "kg/Nm³",
                "label": "Estimated Inlet Dust Loading",
            },
        }

    def initialize(self):
        self.state = {
            "captured_dust_tph": 45.0,
            "clean_gas_nm3h": 65000.0,
            "actual_efficiency_pct": 94.0,
            "draft_loss_mbar": 14.5,
            "heat_loss_gjh": 0.2,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_mix = inlet_streams.get("in_mixture")
        out_gas = outlet_streams.get("out_clean_gas")
        out_dust = outlet_streams.get("out_dust")

        m_in = in_mix.mass_flow_tph if in_mix else 85.0
        t_in = in_mix.temperature_c if in_mix else 380.0
        p_in = in_mix.pressure_mbar if in_mix else -25.0
        v_nm3h = in_mix.volume_flow_nm3h if in_mix and in_mix.volume_flow_nm3h else (m_in * 1000.0 / 1.32)

        eta = float(self.parameters.get("collection_efficiency_pct", 94.0)) / 100.0
        dp = float(self.parameters.get("pressure_drop_mbar", 14.5))
        loading = float(self.parameters.get("solid_loading_kg_nm3", 0.85))

        # Estimate dust mass flow from loading
        total_dust_in_tph = min(m_in * 0.7, (v_nm3h * loading) / 1000.0)
        pure_gas_in_tph = max(1.0, m_in - total_dust_in_tph)

        # Captured vs carryover dust
        captured_dust_tph = total_dust_in_tph * eta
        carryover_tph = total_dust_in_tph * (1.0 - eta)
        clean_gas_out_tph = pure_gas_in_tph + carryover_tph

        self.state["captured_dust_tph"] = round(captured_dust_tph, 2)
        self.state["clean_gas_nm3h"] = round(v_nm3h, 0)
        self.state["actual_efficiency_pct"] = round(eta * 100.0, 1)
        self.state["draft_loss_mbar"] = round(dp, 2)

        # Update clean gas outlet
        if out_gas:
            out_gas.update_state(
                mass_flow_tph=clean_gas_out_tph,
                volume_flow_nm3h=v_nm3h,
                temperature_c=t_in - 5.0,
                pressure_mbar=p_in - dp,
                composition=copy.deepcopy(in_mix.composition) if in_mix else {},
            )

        # Update dust underflow
        if out_dust:
            out_dust.update_state(
                mass_flow_tph=captured_dust_tph,
                temperature_c=t_in - 10.0,
                pressure_mbar=p_in - dp,
                composition={"CaCO3_pct": 78.0, "SiO2_pct": 14.0, "Al2O3_pct": 4.0},
            )

        return outlet_streams
'''

SPLITTER_TEMPLATE_CODE = '''"""
Custom Unit Operation: Proportional Stream Splitter
Splits single incoming material or gas stream into two streams according to user ratio.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class CustomStreamSplitter(BlockBase):
    """
    Tunable Proportional Stream Splitter.
    Divides an incoming process stream into Branch A and Branch B.
    """
    block_type = "CustomStreamSplitter"
    category = "Flow Control"
    icon = "🔱"

    def _define_ports(self) -> List[Port]:
        return [
            Port("in_stream", PortDirection.IN, StreamPhase.SOLID, "Input stream to be split", required=True),
            Port("out_branch_a", PortDirection.OUT, StreamPhase.SOLID, "Branch A primary split", required=True),
            Port("out_branch_b", PortDirection.OUT, StreamPhase.SOLID, "Branch B secondary split", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "split_ratio_a_pct": {
                "type": float,
                "default": 60.0,
                "min": 0.0,
                "max": 100.0,
                "unit": "%",
                "label": "Split Ratio to Branch A",
            },
        }

    def initialize(self):
        self.state = {
            "inlet_flow_tph": 100.0,
            "branch_a_tph": 60.0,
            "branch_b_tph": 40.0,
            "split_ratio_a_pct": 60.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        in_s = inlet_streams.get("in_stream")
        out_a = outlet_streams.get("out_branch_a")
        out_b = outlet_streams.get("out_branch_b")

        m_in = in_s.mass_flow_tph if in_s else 100.0
        t_in = in_s.temperature_c if in_s else 50.0
        p_in = in_s.pressure_mbar if in_s else 0.0

        ratio_a = float(self.parameters.get("split_ratio_a_pct", 60.0)) / 100.0
        ratio_b = max(0.0, 1.0 - ratio_a)

        m_a = m_in * ratio_a
        m_b = m_in * ratio_b

        self.state["inlet_flow_tph"] = round(m_in, 2)
        self.state["branch_a_tph"] = round(m_a, 2)
        self.state["branch_b_tph"] = round(m_b, 2)
        self.state["split_ratio_a_pct"] = round(ratio_a * 100.0, 1)

        comp = copy.deepcopy(in_s.composition) if in_s else {}

        if out_a:
            out_a.update_state(
                mass_flow_tph=m_a,
                temperature_c=t_in,
                pressure_mbar=p_in,
                composition=comp,
            )

        if out_b:
            out_b.update_state(
                mass_flow_tph=m_b,
                temperature_c=t_in,
                pressure_mbar=p_in,
                composition=comp,
            )

        return outlet_streams
'''

MINIMAL_SCAFFOLD_CODE = '''"""
Custom Unit Operation: Minimal Scaffold
Clean starting template for writing proprietary process units.
"""

from typing import Dict, List, Any
import copy

from engine.modular.block_base import BlockBase, Port, PortDirection
from engine.modular.stream import ProcessStream, StreamPhase


class MyCustomBlock(BlockBase):
    """
    My Custom Unit Operation.
    Provide your physics equations and thermodynamic balances below.
    """
    block_type = "MyCustomBlock"
    category = "Custom"
    icon = "📦"

    def _define_ports(self) -> List[Port]:
        """Define inlets and outlets with their allowed StreamPhase (SOLID, GAS, FUEL, AIR, LIQUID)."""
        return [
            Port("in_feed", PortDirection.IN, StreamPhase.SOLID, "Input stream", required=True),
            Port("out_product", PortDirection.OUT, StreamPhase.SOLID, "Output stream", required=True),
        ]

    def _define_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Declare configurable parameters with defaults, limits, and units."""
        return {
            "efficiency_factor": {
                "type": float,
                "default": 1.0,
                "min": 0.1,
                "max": 2.0,
                "unit": "-",
                "label": "Efficiency Multiplier",
            },
        }

    def initialize(self):
        """Declare telemetry variables displayed on cards and sent to OPC UA."""
        self.state = {
            "active_rate_tph": 100.0,
            "temp_c": 50.0,
            "heat_loss_gjh": 0.0,
        }

    def evaluate_steady_state(
        self,
        inlet_streams: Dict[str, ProcessStream],
        outlet_streams: Dict[str, ProcessStream],
    ) -> Dict[str, ProcessStream]:
        """Calculates mass, energy, and species conservation."""
        in_feed = inlet_streams.get("in_feed")
        out_prod = outlet_streams.get("out_product")

        m_in = in_feed.mass_flow_tph if in_feed else 100.0
        t_in = in_feed.temperature_c if in_feed else 50.0
        factor = float(self.parameters.get("efficiency_factor", 1.0))

        m_out = m_in * factor

        self.state["active_rate_tph"] = round(m_out, 2)
        self.state["temp_c"] = round(t_in, 1)

        if out_prod:
            out_prod.update_state(
                mass_flow_tph=m_out,
                temperature_c=t_in,
                pressure_mbar=in_feed.pressure_mbar if in_feed else 0.0,
                composition=copy.deepcopy(in_feed.composition) if in_feed else {},
            )

        return outlet_streams
'''
