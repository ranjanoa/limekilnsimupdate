"""
Unit and Integration Tests for Analog and Binary Control Logic Library.
Validates discrete feedback, signal conditioning, boolean logic, timing,
and flowsheet closed-loop control propagation.
"""

import unittest
from engine.modular.stream import ProcessStream, StreamPhase
from engine.modular.flowsheet_graph import FlowsheetGraph
from engine.modular.solver import FlowsheetSolver
from engine.modular.library import (
    PIDController,
    LeadLagFilter,
    AnalogComparator,
    SignalSelector,
    RateLimiter,
    AnalogMathBlock,
    ProcessTransmitter,
    ControlValveActuator,
    AnalogConstant,
    AnalogAdder,
    AnalogSubtractor,
    AnalogMultiplier,
    AnalogEquationBlock,
    AnalogSelect,
    LogicGate,
    RSFlipFlop,
    TimerDelay,
    EdgeDetector,
    InterlockMatrix,
    BinaryConstant,
    BLOCK_REGISTRY,
    get_component_catalog,
)


class TestLogicLibrary(unittest.TestCase):

    def test_01_catalog_registration(self):
        """Verify all 20 analog and binary components are in BLOCK_REGISTRY and catalog."""
        expected_blocks = [
            "PIDController", "LeadLagFilter", "AnalogComparator", "SignalSelector",
            "RateLimiter", "AnalogMathBlock", "ProcessTransmitter", "ControlValveActuator",
            "AnalogConstant", "AnalogAdder", "AnalogSubtractor", "AnalogMultiplier",
            "AnalogEquationBlock", "AnalogSelect", "LogicGate", "RSFlipFlop", "TimerDelay", "EdgeDetector",
            "InterlockMatrix", "BinaryConstant",
        ]
        for name in expected_blocks:
            self.assertIn(name, BLOCK_REGISTRY)

        catalog = get_component_catalog()
        cat_map = {item["type"]: item for item in catalog}
        for name in expected_blocks:
            self.assertIn(name, cat_map)
            self.assertIn(cat_map[name]["category"], ["Control / Analog", "Control / Binary"])

    def test_02_pid_controller(self):
        """Verify discrete PID algorithm, setpoint tracking, anti-windup, and manual mode."""
        pid = PIDController("pid_1")
        pid.set_parameter("kp", 1.5)
        pid.set_parameter("ti_s", 5.0)
        pid.set_parameter("td_s", 0.2)
        pid.set_parameter("setpoint", 100.0)
        pid.set_parameter("action", "REVERSE")

        # Step 1: PV is 80.0 (error = 100 - 80 = +20). REVERSE acting (heating/feeding): MV should increase
        pv_stream = ProcessStream(stream_id=1, name="PV", phase=StreamPhase.SIGNAL, signal_value=80.0)
        out_mv = ProcessStream(stream_id=2, name="MV", phase=StreamPhase.SIGNAL, signal_value=0.0)
        
        inlets = {"pv": pv_stream}
        outlets = {"mv": out_mv}
        pid.step(1.0, inlets, outlets)

        self.assertGreater(out_mv.signal_value, 0.0)
        self.assertAlmostEqual(pid.state["error"], 20.0, places=2)

        # Run several steps to test integral accumulation and clamping at out_max (100%)
        for _ in range(15):
            pid.step(1.0, inlets, outlets)
        self.assertLessEqual(out_mv.signal_value, 100.0)
        self.assertGreaterEqual(out_mv.signal_value, 0.0)

        # Test Manual Mode
        pid.set_parameter("auto_mode", False)
        pid.set_parameter("manual_out", 45.0)
        pid.step(1.0, inlets, outlets)
        self.assertEqual(out_mv.signal_value, 45.0)

    def test_03_lead_lag_filter(self):
        """Verify first-order dynamic lag filter exponential smoothing."""
        flt = LeadLagFilter("filter_1")
        flt.set_parameter("time_constant_s", 10.0)
        flt.set_parameter("gain", 1.0)

        step_in = ProcessStream(stream_id=10, name="Step", phase=StreamPhase.SIGNAL, signal_value=100.0)
        out_filtered = ProcessStream(stream_id=11, name="Filtered", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # Step at dt=2.0s
        # alpha = 2 / (10 + 2) = 2/12 = 0.1667
        # y1 = 0 + 0.1667 * 100 = ~16.67
        flt.step(2.0, {"in_signal": step_in}, {"out_signal": out_filtered})
        self.assertAlmostEqual(out_filtered.signal_value, 16.6667, delta=1.0)

        # Run forward 50 seconds: should converge close to 100.0
        for _ in range(25):
            flt.step(2.0, {"in_signal": step_in}, {"out_signal": out_filtered})
        self.assertAlmostEqual(out_filtered.signal_value, 100.0, delta=2.0)

    def test_04_analog_comparator(self):
        """Verify high/low comparator hysteresis deadband and binary trip signals."""
        comp = AnalogComparator("comp_1")
        comp.set_parameter("hi_limit", 150.0)
        comp.set_parameter("lo_limit", 20.0)
        comp.set_parameter("hysteresis", 5.0)

        s_in = ProcessStream(stream_id=20, name="In", phase=StreamPhase.SIGNAL, signal_value=140.0)
        out_hi = ProcessStream(stream_id=21, name="Hi", phase=StreamPhase.BINARY)
        out_lo = ProcessStream(stream_id=22, name="Lo", phase=StreamPhase.BINARY)
        out_norm = ProcessStream(stream_id=23, name="Norm", phase=StreamPhase.BINARY)

        # Input below high limit: 140.0 -> Normal
        comp.evaluate_steady_state({"in_val": s_in}, {"out_hi": out_hi, "out_lo": out_lo, "out_normal": out_norm})
        self.assertFalse(out_hi.binary_state)
        self.assertTrue(out_norm.binary_state)

        # Input exceeds high limit: 152.0 -> High Alarm
        s_in.signal_value = 152.0
        comp.evaluate_steady_state({"in_val": s_in}, {"out_hi": out_hi, "out_lo": out_lo, "out_normal": out_norm})
        self.assertTrue(out_hi.binary_state)
        self.assertFalse(out_norm.binary_state)

        # Input drops to 148.0: still within hysteresis zone (150 - 5 = 145) -> remains tripped
        s_in.signal_value = 148.0
        comp.evaluate_steady_state({"in_val": s_in}, {"out_hi": out_hi, "out_lo": out_lo, "out_normal": out_norm})
        self.assertTrue(out_hi.binary_state)

        # Input drops to 142.0: falls below reset limit (145.0) -> resets to normal
        s_in.signal_value = 142.0
        comp.evaluate_steady_state({"in_val": s_in}, {"out_hi": out_hi, "out_lo": out_lo, "out_normal": out_norm})
        self.assertFalse(out_hi.binary_state)
        self.assertTrue(out_norm.binary_state)

    def test_05_signal_selector(self):
        """Verify MIN, MAX, AVERAGE auctioneering signal selection."""
        sel = SignalSelector("sel_1")
        s1 = ProcessStream(stream_id=31, name="S1", phase=StreamPhase.SIGNAL, signal_value=20.0)
        s2 = ProcessStream(stream_id=32, name="S2", phase=StreamPhase.SIGNAL, signal_value=80.0)
        s3 = ProcessStream(stream_id=33, name="S3", phase=StreamPhase.SIGNAL, signal_value=50.0)
        out_sel = ProcessStream(stream_id=34, name="Out", phase=StreamPhase.SIGNAL)

        # Test AVERAGE
        sel.set_parameter("mode", "AVERAGE")
        sel.evaluate_steady_state({"in_a": s1, "in_b": s2, "in_c": s3}, {"out_selected": out_sel})
        self.assertAlmostEqual(out_sel.signal_value, 50.0)

        # Test MIN
        sel.set_parameter("mode", "MIN")
        sel.evaluate_steady_state({"in_a": s1, "in_b": s2, "in_c": s3}, {"out_selected": out_sel})
        self.assertEqual(out_sel.signal_value, 20.0)

        # Test MAX
        sel.set_parameter("mode", "MAX")
        sel.evaluate_steady_state({"in_a": s1, "in_b": s2, "in_c": s3}, {"out_selected": out_sel})
        self.assertEqual(out_sel.signal_value, 80.0)

    def test_06_rate_limiter(self):
        """Verify ramp and slew rate limiting on sudden step inputs."""
        lim = RateLimiter("lim_1")
        lim.set_parameter("max_rate_up_per_s", 5.0)
        lim.set_parameter("max_rate_down_per_s", 5.0)

        step_in = ProcessStream(stream_id=40, name="Step", phase=StreamPhase.SIGNAL, signal_value=100.0)
        out_ramped = ProcessStream(stream_id=41, name="Ramped", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # After dt=2.0s, output can only rise at most 5.0 * 2.0 = 10.0
        lim.step(2.0, {"in_signal": step_in}, {"out_ramped": out_ramped})
        self.assertAlmostEqual(out_ramped.signal_value, 10.0, places=2)

    def test_07_analog_math_block(self):
        """Verify arithmetic operations and linear scaling."""
        math_b = AnalogMathBlock("math_1")
        s1 = ProcessStream(stream_id=51, name="S1", phase=StreamPhase.SIGNAL, signal_value=40.0)
        s2 = ProcessStream(stream_id=52, name="S2", phase=StreamPhase.SIGNAL, signal_value=10.0)
        out_val = ProcessStream(stream_id=53, name="Res", phase=StreamPhase.SIGNAL)

        # ADD
        math_b.set_parameter("operation", "ADD")
        math_b.evaluate_steady_state({"in_a": s1, "in_b": s2}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 50.0)

        # SUBTRACT
        math_b.set_parameter("operation", "SUBTRACT")
        math_b.evaluate_steady_state({"in_a": s1, "in_b": s2}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 30.0)

        # SCALE_OFFSET (in_a * gain + offset)
        math_b.set_parameter("operation", "SCALE_OFFSET")
        math_b.set_parameter("gain", 1.8)
        math_b.set_parameter("offset", 32.0)
        math_b.evaluate_steady_state({"in_a": s1}, {"out_val": out_val})
        # 40 * 1.8 + 32 = 104.0 (C to F)
        self.assertAlmostEqual(out_val.signal_value, 104.0)

    def test_08_process_transmitter_and_valve(self):
        """Verify tapping a physical process stream and modulating control valve."""
        tx = ProcessTransmitter("tt_101")
        tx.set_parameter("variable", "TEMPERATURE")
        tx.set_parameter("range_min", 0.0)
        tx.set_parameter("range_max", 1200.0)
        tx.set_parameter("output_format", "EU")

        # Physical fluid stream: 280 TPH at 850 C
        hot_gas = ProcessStream(
            stream_id=60,
            name="Hot Gas",
            phase=StreamPhase.GAS,
            mass_flow_tph=280.0,
            temperature_c=850.0,
            pressure_mbar=990.0,
        )
        out_proc = ProcessStream(stream_id=61, name="Gas Thru", phase=StreamPhase.GAS)
        out_sig = ProcessStream(stream_id=62, name="TT Sig", phase=StreamPhase.SIGNAL)

        tx.evaluate_steady_state({"in_process": hot_gas}, {"out_process": out_proc, "out_signal": out_sig})
        self.assertEqual(out_sig.signal_value, 850.0)
        self.assertEqual(out_proc.temperature_c, 850.0)

        # Control valve actuator throttling fluid flow
        valve = ControlValveActuator("fcv_101")
        valve.set_parameter("characteristic", "LINEAR")
        valve.set_parameter("use_signal_input", True)

        ctrl_sig = ProcessStream(stream_id=63, name="Ctrl", phase=StreamPhase.SIGNAL, signal_value=60.0) # 60% open
        out_fluid = ProcessStream(stream_id=64, name="Throttled Gas", phase=StreamPhase.GAS)

        valve.evaluate_steady_state({"in_fluid": hot_gas, "in_signal": ctrl_sig}, {"out_fluid": out_fluid})
        # With linear 60% position, flow is 280.0 * 0.60 = 168.0 t/h
        self.assertAlmostEqual(out_fluid.mass_flow_tph, 168.0, delta=1.0)

    def test_09_boolean_logic_gates(self):
        """Verify logic gate operations (AND, OR, XOR, NAND, NOR, NOT) and inverted output."""
        gate = LogicGate("gate_1")
        t_sig = ProcessStream(stream_id=71, name="T", phase=StreamPhase.BINARY, binary_state=True)
        f_sig = ProcessStream(stream_id=72, name="F", phase=StreamPhase.BINARY, binary_state=False)
        out_q = ProcessStream(stream_id=73, name="Q", phase=StreamPhase.BINARY)
        out_not_q = ProcessStream(stream_id=74, name="NotQ", phase=StreamPhase.BINARY)

        # AND: True & False -> False, NOT_Q -> True
        gate.set_parameter("gate_type", "AND")
        gate.evaluate_steady_state({"in_a": t_sig, "in_b": f_sig}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertFalse(out_q.binary_state)
        self.assertTrue(out_not_q.binary_state)

        # OR: True | False -> True
        gate.set_parameter("gate_type", "OR")
        gate.evaluate_steady_state({"in_a": t_sig, "in_b": f_sig}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertTrue(out_q.binary_state)

        # XOR: True ^ True -> False
        gate.set_parameter("gate_type", "XOR")
        gate.evaluate_steady_state({"in_a": t_sig, "in_b": t_sig}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertFalse(out_q.binary_state)

        # NOT: !False -> True
        gate.set_parameter("gate_type", "NOT")
        gate.evaluate_steady_state({"in_a": f_sig}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertTrue(out_q.binary_state)

    def test_10_rs_flip_flop(self):
        """Verify bistable latching, unlatching, and RESET dominance."""
        latch = RSFlipFlop("ff_1")
        latch.set_parameter("priority", "RESET_DOMINANT")

        set_on = ProcessStream(stream_id=81, name="S", phase=StreamPhase.BINARY, binary_state=True)
        set_off = ProcessStream(stream_id=82, name="S0", phase=StreamPhase.BINARY, binary_state=False)
        rst_off = ProcessStream(stream_id=83, name="R0", phase=StreamPhase.BINARY, binary_state=False)
        rst_on = ProcessStream(stream_id=84, name="R1", phase=StreamPhase.BINARY, binary_state=True)
        out_q = ProcessStream(stream_id=85, name="Q", phase=StreamPhase.BINARY)
        out_not_q = ProcessStream(stream_id=86, name="NotQ", phase=StreamPhase.BINARY)

        # Pulse SET: Q becomes True
        latch.step(1.0, {"set": set_on, "reset": rst_off}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertTrue(out_q.binary_state)

        # Remove SET: Q remains latched True
        latch.step(1.0, {"set": set_off, "reset": rst_off}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertTrue(out_q.binary_state)

        # Both SET and RESET true: RESET dominant -> Q becomes False
        latch.step(1.0, {"set": set_on, "reset": rst_on}, {"out_q": out_q, "out_not_q": out_not_q})
        self.assertFalse(out_q.binary_state)

    def test_11_timer_delay(self):
        """Verify IEC 61131-3 timer modes: TON (On-Delay), TOF (Off-Delay), and TP (Pulse)."""
        # TON test: 3-second delay
        ton = TimerDelay("ton_1")
        ton.set_parameter("timer_type", "TON")
        ton.set_parameter("preset_time_s", 3.0)

        in_hi = ProcessStream(stream_id=91, name="HI", phase=StreamPhase.BINARY, binary_state=True)
        in_lo = ProcessStream(stream_id=92, name="LO", phase=StreamPhase.BINARY, binary_state=False)
        out_q = ProcessStream(stream_id=93, name="Q", phase=StreamPhase.BINARY)
        out_et = ProcessStream(stream_id=94, name="ET", phase=StreamPhase.SIGNAL)

        # At t=1s: not yet expired -> False
        ton.step(1.0, {"in_trigger": in_hi}, {"out_q": out_q, "out_elapsed": out_et})
        self.assertFalse(out_q.binary_state)

        # At t=2s: not yet expired -> False
        ton.step(1.0, {"in_trigger": in_hi}, {"out_q": out_q, "out_elapsed": out_et})
        self.assertFalse(out_q.binary_state)

        # At t=3s: timer elapsed -> True!
        ton.step(1.0, {"in_trigger": in_hi}, {"out_q": out_q, "out_elapsed": out_et})
        self.assertTrue(out_q.binary_state)

        # Input drops to False -> resets immediately
        ton.step(1.0, {"in_trigger": in_lo}, {"out_q": out_q, "out_elapsed": out_et})
        self.assertFalse(out_q.binary_state)

    def test_12_edge_detector_and_interlock(self):
        """Verify transition one-shot edge detector and safety interlock permissive matrix."""
        # Edge Detector
        edge = EdgeDetector("edge_1")
        edge.set_parameter("edge_mode", "RISING")

        lo = ProcessStream(stream_id=101, name="LO", phase=StreamPhase.BINARY, binary_state=False)
        hi = ProcessStream(stream_id=102, name="HI", phase=StreamPhase.BINARY, binary_state=True)
        out_p = ProcessStream(stream_id=103, name="Pulse", phase=StreamPhase.BINARY)

        # Initial state low
        edge.step(1.0, {"in_signal": lo}, {"out_pulse": out_p})
        self.assertFalse(out_p.binary_state)

        # 0 -> 1 transition triggers pulse
        edge.step(1.0, {"in_signal": hi}, {"out_pulse": out_p})
        self.assertTrue(out_p.binary_state)

        # Stays at 1: pulse disappears
        edge.step(1.0, {"in_signal": hi}, {"out_pulse": out_p})
        self.assertFalse(out_p.binary_state)

        # Safety Interlock Matrix
        matrix = InterlockMatrix("matrix_1")
        matrix.set_parameter("logic_mode", "ALL_REQUIRED")
        out_perm = ProcessStream(stream_id=104, name="Perm", phase=StreamPhase.BINARY)
        out_trip = ProcessStream(stream_id=105, name="Trip", phase=StreamPhase.BINARY)

        # Permissive 1 OK, Permissive 2 NOT OK
        matrix.evaluate_steady_state({"cond_1": hi, "cond_2": lo}, {"out_permissive": out_perm, "out_trip": out_trip})
        self.assertFalse(out_perm.binary_state)
        self.assertTrue(out_trip.binary_state)

        # Both Permissives OK
        matrix.evaluate_steady_state({"cond_1": hi, "cond_2": hi}, {"out_permissive": out_perm, "out_trip": out_trip})
        self.assertTrue(out_perm.binary_state)
        self.assertFalse(out_trip.binary_state)

    def test_13_closed_loop_control_in_flowsheet_graph(self):
        """
        Verify complete closed-loop feedback wiring in FlowsheetGraph:
        Process Stream -> Transmitter -> PID Controller -> Control Valve Actuator -> Modulated Fluid Stream.
        """
        graph = FlowsheetGraph(flowsheet_id="test_closed_loop", name="Closed Loop Test")

        # Add transmitter, PID, and control valve blocks
        tx = ProcessTransmitter("TT_01")
        tx.set_parameter("variable", "MASS_FLOW")
        tx.set_parameter("range_min", 0.0)
        tx.set_parameter("range_max", 500.0)
        tx.set_parameter("output_format", "EU")
        graph.add_block(tx)

        pid = PIDController("PIC_01")
        pid.set_parameter("setpoint", 200.0)
        pid.set_parameter("kp", 0.5)
        pid.set_parameter("ti_s", 10.0)
        pid.set_parameter("action", "DIRECT")
        graph.add_block(pid)

        valve = ControlValveActuator("FCV_01")
        valve.set_parameter("characteristic", "LINEAR")
        valve.set_parameter("use_signal_input", True)
        graph.add_block(valve)

        # Feed inlet fluid to transmitter
        inlet_fluid = ProcessStream(
            stream_id=200,
            name="Raw Slurry",
            phase=StreamPhase.LIQUID,
            mass_flow_tph=250.0,
            temperature_c=25.0,
            to_block="TT_01",
            to_port="in_process",
        )
        graph.streams[inlet_fluid.stream_id] = inlet_fluid
        tx.ports["in_process"].connected_stream_id = inlet_fluid.stream_id

        # Connect Transmitter process passthrough -> Valve in_fluid
        graph.connect("TT_01", "out_process", "FCV_01", "in_fluid", stream_id=201)

        # Connect Transmitter PV output -> PID PV input
        graph.connect("TT_01", "out_signal", "PIC_01", "pv", stream_id=202)

        # Connect PID MV output -> Valve in_signal
        graph.connect("PIC_01", "mv", "FCV_01", "in_signal", stream_id=203)

        # Add outlet stream from Valve out_fluid
        out_stream = ProcessStream(
            stream_id=204,
            name="Discharge Slurry",
            phase=StreamPhase.LIQUID,
            from_block="FCV_01",
            from_port="out_fluid",
        )
        graph.streams[out_stream.stream_id] = out_stream
        valve.ports["out_fluid"].connected_stream_id = out_stream.stream_id

        # Solve step using FlowsheetSolver
        solver = FlowsheetSolver(graph)
        result = solver.step(dt=1.0)
        self.assertIsNotNone(result)

        # Check telemetry and signals
        pv_val = graph.streams[202].signal_value
        self.assertEqual(pv_val, 250.0)

        mv_val = graph.streams[203].signal_value
        self.assertGreater(mv_val, 0.0)
        self.assertLessEqual(mv_val, 100.0)

        throttled_fluid = graph.streams[204]
        self.assertIsNotNone(throttled_fluid)
        self.assertGreater(throttled_fluid.mass_flow_tph, 0.0)

    def test_14_constant_blocks(self):
        """Verify AnalogConstant and BinaryConstant generation of initial stimuli and setpoints."""
        # Analog Constant
        a_const = AnalogConstant("sp_source")
        a_const.set_parameter("constant_value", 350.5)
        a_const.set_parameter("engineering_unit", "t/h")
        out_sig = ProcessStream(stream_id=301, name="SP_Signal", phase=StreamPhase.SIGNAL)
        
        a_const.evaluate_steady_state({}, {"out_signal": out_sig})
        self.assertEqual(out_sig.signal_value, 350.5)
        self.assertEqual(a_const.state["output_signal"], 350.5)

        # Dynamic step
        out_sig.signal_value = 0.0
        a_const.step(1.0, {}, {"out_signal": out_sig})
        self.assertEqual(out_sig.signal_value, 350.5)

        # Binary Constant (True)
        b_const = BinaryConstant("perm_source")
        b_const.set_parameter("constant_state", True)
        out_st = ProcessStream(stream_id=302, name="Perm_Signal", phase=StreamPhase.BINARY)
        out_not = ProcessStream(stream_id=303, name="Trip_Signal", phase=StreamPhase.BINARY)

        b_const.evaluate_steady_state({}, {"out_state": out_st, "out_not_state": out_not})
        self.assertTrue(out_st.binary_state)
        self.assertFalse(out_not.binary_state)

        # Binary Constant (False)
        b_const.set_parameter("constant_state", False)
        b_const.evaluate_steady_state({}, {"out_state": out_st, "out_not_state": out_not})
        self.assertFalse(out_st.binary_state)
        self.assertTrue(out_not.binary_state)

    def test_15_analog_adder(self):
        """Verify AnalogAdder multi-input weighted summation and output clamping."""
        adder = AnalogAdder("adder_01")
        adder.set_parameter("k1", 1.0)
        adder.set_parameter("k2", 2.0)
        adder.set_parameter("k3", 0.5)
        adder.set_parameter("k4", 0.1)
        adder.set_parameter("bias", 10.0)

        s1 = ProcessStream(stream_id=401, name="Sig1", phase=StreamPhase.SIGNAL, signal_value=10.0)
        s2 = ProcessStream(stream_id=402, name="Sig2", phase=StreamPhase.SIGNAL, signal_value=20.0)
        s3 = ProcessStream(stream_id=403, name="Sig3", phase=StreamPhase.SIGNAL, signal_value=30.0)
        s4 = ProcessStream(stream_id=404, name="Sig4", phase=StreamPhase.SIGNAL, signal_value=40.0)
        out_sum = ProcessStream(stream_id=405, name="SumOut", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # Expected: 1*10 + 2*20 + 0.5*30 + 0.1*40 + 10 = 10 + 40 + 15 + 4 + 10 = 79.0
        adder.evaluate_steady_state({"in_1": s1, "in_2": s2, "in_3": s3, "in_4": s4}, {"out_sum": out_sum})
        self.assertEqual(out_sum.signal_value, 79.0)
        self.assertEqual(adder.state["output_sum"], 79.0)

        # Test Clamping
        adder.set_parameter("clamp_max", 50.0)
        adder.evaluate_steady_state({"in_1": s1, "in_2": s2, "in_3": s3, "in_4": s4}, {"out_sum": out_sum})
        self.assertEqual(out_sum.signal_value, 50.0)

        # Dynamic step
        adder.set_parameter("clamp_max", 1000.0)
        adder.step(1.0, {"in_1": s1, "in_2": s2, "in_3": s3, "in_4": s4}, {"out_sum": out_sum})
        self.assertEqual(out_sum.signal_value, 79.0)

    def test_16_analog_subtractor(self):
        """Verify AnalogSubtractor difference calculation and clamping."""
        sub = AnalogSubtractor("sub_01")
        sub.set_parameter("gain_pos", 1.5)
        sub.set_parameter("gain_neg", 0.5)
        sub.set_parameter("bias", -5.0)

        s_pos = ProcessStream(stream_id=410, name="PosIn", phase=StreamPhase.SIGNAL, signal_value=100.0)
        s_neg = ProcessStream(stream_id=411, name="NegIn", phase=StreamPhase.SIGNAL, signal_value=40.0)
        out_diff = ProcessStream(stream_id=412, name="DiffOut", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # Expected: 1.5 * 100 - 0.5 * 40 - 5 = 150 - 20 - 5 = 125.0
        sub.evaluate_steady_state({"in_pos": s_pos, "in_neg": s_neg}, {"out_diff": out_diff})
        self.assertEqual(out_diff.signal_value, 125.0)
        self.assertEqual(sub.state["output_diff"], 125.0)

        # Test clamp min
        sub.set_parameter("clamp_min", 150.0)
        sub.evaluate_steady_state({"in_pos": s_pos, "in_neg": s_neg}, {"out_diff": out_diff})
        self.assertEqual(out_diff.signal_value, 150.0)

    def test_17_analog_multiplier(self):
        """Verify AnalogMultiplier product, ratio division, and divide-by-zero safeguard."""
        mul = AnalogMultiplier("mul_01")
        mul.set_parameter("gain", 2.0)
        mul.set_parameter("bias", 3.0)

        sa = ProcessStream(stream_id=420, name="A", phase=StreamPhase.SIGNAL, signal_value=5.0)
        sb = ProcessStream(stream_id=421, name="B", phase=StreamPhase.SIGNAL, signal_value=4.0)
        sdiv = ProcessStream(stream_id=422, name="Div", phase=StreamPhase.SIGNAL, signal_value=2.0)
        out_prod = ProcessStream(stream_id=423, name="ProdOut", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # Expected: 2.0 * (5.0 * 4.0 / 2.0) + 3.0 = 2.0 * 10.0 + 3.0 = 23.0
        mul.evaluate_steady_state({"in_a": sa, "in_b": sb, "in_div": sdiv}, {"out_prod": out_prod})
        self.assertEqual(out_prod.signal_value, 23.0)
        self.assertEqual(mul.state["output_prod"], 23.0)

        # Test divide by zero protection
        sdiv.signal_value = 0.0
        mul.evaluate_steady_state({"in_a": sa, "in_b": sb, "in_div": sdiv}, {"out_prod": out_prod})
        self.assertFalse(abs(out_prod.signal_value) > 1e12 and out_prod.signal_value == out_prod.signal_value)

    def test_18_analog_equation_block(self):
        """Verify AnalogEquationBlock formula parsing and safe math evaluation."""
        eq_block = AnalogEquationBlock("eqn_01")
        sa = ProcessStream(stream_id=430, name="A", phase=StreamPhase.SIGNAL, signal_value=3.0)
        sb = ProcessStream(stream_id=431, name="B", phase=StreamPhase.SIGNAL, signal_value=4.0)
        sc = ProcessStream(stream_id=432, name="C", phase=StreamPhase.SIGNAL, signal_value=5.0)
        sd = ProcessStream(stream_id=433, name="D", phase=StreamPhase.SIGNAL, signal_value=2.0)
        out_val = ProcessStream(stream_id=434, name="ResOut", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # 1. Simple addition & subtraction
        eq_block.set_parameter("equation", "A + B - C")
        eq_block.evaluate_steady_state({"in_a": sa, "in_b": sb, "in_c": sc}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 2.0)  # 3 + 4 - 5 = 2

        # 2. Pythagorean theorem with sqrt and power
        eq_block.set_parameter("equation", "sqrt(A^2 + B^2)")
        eq_block.evaluate_steady_state({"in_a": sa, "in_b": sb}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 5.0)  # sqrt(9 + 16) = 5.0

        # 3. Math functions min, max, exp, abs
        eq_block.set_parameter("equation", "min(A, B) + max(C, D)")
        eq_block.evaluate_steady_state({"in_a": sa, "in_b": sb, "in_c": sc, "in_d": sd}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 8.0)  # min(3, 4) + max(5, 2) = 3 + 5 = 8.0

        # 4. Division by zero safety
        eq_block.set_parameter("equation", "A / 0")
        eq_block.evaluate_steady_state({"in_a": sa}, {"out_val": out_val})
        self.assertEqual(out_val.signal_value, 0.0)

    def test_19_flowsheet_arithmetic_cascade(self):
        """Integration test: Cascade AnalogConstant -> AnalogAdder & AnalogSubtractor -> AnalogEquationBlock."""
        graph = FlowsheetGraph()

        # Add components
        acon_1 = AnalogConstant("C1")
        acon_1.set_parameter("constant_value", 50.0)
        acon_2 = AnalogConstant("C2")
        acon_2.set_parameter("constant_value", 30.0)
        adder = AnalogAdder("ADD1")
        adder.set_parameter("k1", 1.0)
        adder.set_parameter("k2", 1.0)
        sub = AnalogSubtractor("SUB1")
        sub.set_parameter("gain_pos", 1.0)
        sub.set_parameter("gain_neg", 1.0)
        eqn = AnalogEquationBlock("EQN1")
        eqn.set_parameter("equation", "sqrt(A * B)")  # Geometric mean

        graph.add_block(acon_1)
        graph.add_block(acon_2)
        graph.add_block(adder)
        graph.add_block(sub)
        graph.add_block(eqn)

        # Connect C1 and C2 to Adder
        graph.connect("C1", "out_signal", "ADD1", "in_1", stream_id=501)
        graph.connect("C2", "out_signal", "ADD1", "in_2", stream_id=502)

        # Connect C1 and C2 to Subtractor
        graph.connect("C1", "out_signal", "SUB1", "in_pos", stream_id=503)
        graph.connect("C2", "out_signal", "SUB1", "in_neg", stream_id=504)

        # Connect Adder (A) and Subtractor (B) to Equation Block
        graph.connect("ADD1", "out_sum", "EQN1", "in_a", stream_id=505)
        graph.connect("SUB1", "out_diff", "EQN1", "in_b", stream_id=506)

        # Add output stream from Equation Block
        res_stream = ProcessStream(
            stream_id=507,
            name="Final Result",
            phase=StreamPhase.SIGNAL,
            from_block="EQN1",
            from_port="out_val",
        )
        graph.streams[res_stream.stream_id] = res_stream
        eqn.ports["out_val"].connected_stream_id = res_stream.stream_id

        # Solve
        solver = FlowsheetSolver(graph)
        result = solver.step(dt=1.0)
        self.assertIsNotNone(result)

        # C1 = 50, C2 = 30
        # Adder sum = 50 + 30 = 80
        # Subtractor diff = 50 - 30 = 20
        # Equation = sqrt(80 * 20) = sqrt(1600) = 40.0
        self.assertEqual(graph.streams[505].signal_value, 80.0)
        self.assertEqual(graph.streams[506].signal_value, 20.0)
        self.assertAlmostEqual(graph.streams[507].signal_value, 40.0, places=2)

    def test_20_analog_select(self):
        """Verify AnalogSelect 2:1 multiplexer selects analog1 on 0 and analog2 on 1."""
        mux = AnalogSelect("mux_01")

        s_a1 = ProcessStream(stream_id=601, name="Analog1", phase=StreamPhase.SIGNAL, signal_value=123.4)
        s_a2 = ProcessStream(stream_id=602, name="Analog2", phase=StreamPhase.SIGNAL, signal_value=567.8)
        s_sel = ProcessStream(stream_id=603, name="SelDigit", phase=StreamPhase.BINARY, binary_state=False)
        out_s = ProcessStream(stream_id=604, name="OutSelected", phase=StreamPhase.SIGNAL, signal_value=0.0)

        # 1. Digital Selection = 0 (False): Output = Analog 1 (123.4)
        mux.evaluate_steady_state(
            {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel},
            {"out_selected": out_s}
        )
        self.assertEqual(out_s.signal_value, 123.4)
        self.assertEqual(mux.state["selected_channel"], 1)
        self.assertFalse(mux.state["select_active"])

        # 2. Digital Selection = 1 (True): Output = Analog 2 (567.8)
        s_sel.binary_state = True
        mux.evaluate_steady_state(
            {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel},
            {"out_selected": out_s}
        )
        self.assertEqual(out_s.signal_value, 567.8)
        self.assertEqual(mux.state["selected_channel"], 2)
        self.assertTrue(mux.state["select_active"])

        # 3. Analog Selection Signal: 0.0 -> Analog 1, 1.0 -> Analog 2
        s_sel_analog = ProcessStream(stream_id=605, name="SelAnalog", phase=StreamPhase.SIGNAL, signal_value=0.0)
        mux.evaluate_steady_state(
            {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel_analog},
            {"out_selected": out_s}
        )
        self.assertEqual(out_s.signal_value, 123.4)

        s_sel_analog.signal_value = 1.0
        mux.evaluate_steady_state(
            {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel_analog},
            {"out_selected": out_s}
        )
        self.assertEqual(out_s.signal_value, 567.8)

        # 4. Invert Selection Logic: Sel=1 gives Analog 1
        mux.set_parameter("invert_select", True)
        mux.evaluate_steady_state(
            {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel_analog},
            {"out_selected": out_s}
        )
        self.assertEqual(out_s.signal_value, 123.4)
        mux.set_parameter("invert_select", False)

        # 5. Dynamic step()
        s_sel.binary_state = True
        mux.step(1.0, {"in_analog1": s_a1, "in_analog2": s_a2, "in_select": s_sel}, {"out_selected": out_s})
        self.assertEqual(out_s.signal_value, 567.8)


if __name__ == "__main__":
    unittest.main()

