/**
 * INDUSTRIAL DCS CONTROLLER ENGINE
 * Closed-Loop Interacting Controllers (PID with Anti-Windup & Feedforward)
 * Tailored for Siemens SIMIT / PCS 7 Pyroprocessing Control Strategies
 */

class PIDController {
  constructor(options) {
    this.name = options.name || 'PID';
    this.kp = options.kp || 1.0;
    this.ti = options.ti || 60.0; // Integral reset time (seconds)
    this.td = options.td || 0.0;  // Derivative time (seconds)
    this.outMin = options.outMin !== undefined ? options.outMin : 0.0;
    this.outMax = options.outMax !== undefined ? options.outMax : 100.0;
    this.reverseActing = options.reverseActing || false;

    this.mode = 'AUTO';           // 'AUTO' or 'MAN'
    this.sp = options.sp || 0.0;
    this.pv = options.sp || 0.0;
    this.op = options.op || 50.0;
    this.manualOp = this.op;

    // Initialize integral term to nominal OP so when error = 0, output is nominal OP
    this.integral = this.op;
    this.lastError = 0.0;
    this.lastPv = this.pv;
  }

  setMode(newMode) {
    if (newMode === 'MAN' && this.mode === 'AUTO') {
      this.mode = 'MAN';
      this.manualOp = this.op; // Bumpless AUTO -> MAN
    } else if (newMode === 'AUTO' && this.mode === 'MAN') {
      this.mode = 'AUTO';
      // Bumpless MAN -> AUTO: preset integral so OP does not jump
      const error = this.reverseActing ? (this.pv - this.sp) : (this.sp - this.pv);
      this.integral = this.manualOp - (this.kp * error);
      this.lastError = error;
    }
  }

  update(pv, dt, feedforward = 0.0) {
    this.pv = pv;

    if (this.mode === 'MAN') {
      this.op = Math.max(this.outMin, Math.min(this.outMax, this.manualOp));
      const error = this.reverseActing ? (this.pv - this.sp) : (this.sp - this.pv);
      this.integral = this.op - (this.kp * error);
      this.lastError = error;
      return this.op;
    }

    // AUTO Mode: Standard industrial ISA PID algorithm
    const error = this.reverseActing ? (this.pv - this.sp) : (this.sp - this.pv);

    // Proportional Term
    const pTerm = this.kp * error;

    // Integral Term with Trapezoidal Integration & Anti-Windup Clamp
    if (this.ti > 0.0) {
      this.integral += (this.kp / this.ti) * error * dt;
      // Clamp integral
      this.integral = Math.max(this.outMin, Math.min(this.outMax, this.integral));
    }

    // Derivative Term (on measurement to avoid derivative kick)
    let dTerm = 0.0;
    if (this.td > 0.0 && dt > 0.0) {
      const dPv = (this.pv - this.lastPv) / dt;
      dTerm = -this.kp * this.td * dPv;
    }

    // Total Control Output
    let rawOp = pTerm + this.integral + dTerm + feedforward;

    // Output Saturation Clamp
    this.op = Math.max(this.outMin, Math.min(this.outMax, rawOp));

    // Anti-Windup Clamping: if saturated, back off integral
    if (rawOp > this.outMax && error > 0) {
      this.integral -= (rawOp - this.outMax);
    } else if (rawOp < this.outMin && error < 0) {
      this.integral -= (rawOp - this.outMin);
    }

    this.lastError = error;
    this.lastPv = pv;
    return this.op;
  }
}

class PyroprocessControlSystem {
  constructor() {
    this.initControllers();
  }

  initControllers() {
    // 1. Raw Meal Feed Rate Controller (FIC_FEED)
    this.ficFeed = new PIDController({
      name: 'FIC-FEED',
      kp: 1.0,
      ti: 10.0,
      sp: 280.0,
      op: 280.0,
      outMin: 150.0,
      outMax: 350.0
    });

    // 2. Precalciner Temperature Controller (TIC_PC)
    // Manipulates fuel to precalciner (OP: nominal 54.1%)
    this.ticPc = new PIDController({
      name: 'TIC-PC',
      kp: 0.25,
      ti: 20.0,
      td: 2.0,
      sp: 907.0,
      op: 54.1,
      outMin: 20.0,
      outMax: 100.0
    });

    // 3. Burning Zone Temperature & Free Lime Controller (TIC_BZ)
    // Manipulates kiln main burner fuel (OP: nominal 45.9%)
    this.ticBz = new PIDController({
      name: 'TIC-BZ',
      kp: 0.15,
      ti: 35.0,
      td: 3.0,
      sp: 1450.0,
      op: 45.9,
      outMin: 15.0,
      outMax: 90.0
    });

    // 4. Preheater Top Draft Controller (PIC_PH)
    // Manipulates ID fan damper K3G37 (nominal 92%)
    this.picPh = new PIDController({
      name: 'PIC-PH',
      kp: 1.2,
      ti: 6.0,
      td: 0.5,
      sp: -56.0,
      op: 92.0,
      outMin: 20.0,
      outMax: 100.0,
      reverseActing: true
    });

    // 5. Kiln Hood Pressure Controller (PIC_KH)
    // Manipulates Cooler Exhaust Vent Fan speed / damper L3M366 (nominal 75.5%)
    this.picKh = new PIDController({
      name: 'PIC-KH',
      kp: 25.0,
      ti: 3.0,
      td: 0.2,
      sp: -0.30,
      op: 75.5,
      outMin: 20.0,
      outMax: 100.0,
      reverseActing: true
    });

    // 6. Kiln Oxygen / Air Ratio Controller (AIC_O2)
    // Adjusts Tertiary air damper / secondary air balance
    this.aicO2 = new PIDController({
      name: 'AIC-O2',
      kp: 10.0,
      ti: 15.0,
      sp: 2.32,
      op: 99.0,
      outMin: 20.0,
      outMax: 100.0
    });
  }

  /**
   * Run All Interacting Control Loops
   * @param {CementProcessModel} model - The physics plant model
   * @param {number} dt - Time step in seconds
   * @returns {Object} Actuator demands to pass to physics model
   */
  execute(model, dt) {
    // Loop 1: Feed Controller
    // In AUTO mode, setpoint directly sets feed rate demand to weigh feeders
    let feedOp;
    if (this.ficFeed.mode === 'AUTO') {
      feedOp = this.ficFeed.sp;
      this.ficFeed.op = feedOp;
      this.ficFeed.pv = model.rawMealFeed;
    } else {
      feedOp = this.ficFeed.manualOp;
      this.ficFeed.op = feedOp;
      this.ficFeed.pv = model.rawMealFeed;
    }

    // Feedforward decoupling:
    // When raw meal feed changes, inject immediate proportional fuel trim
    const feedDeltaNorm = (feedOp - 280.0) / 280.0;
    const ffPc = feedDeltaNorm * 20.0;   // Precalciner feedforward trim
    const ffKiln = feedDeltaNorm * 12.0; // Kiln burner feedforward trim

    // Loop 2: Precalciner Temperature
    const pcFuelOp = this.ticPc.update(model.pcExitTemp, dt, ffPc);

    // Loop 3: Burning Zone Temperature
    const kilnFuelOp = this.ticBz.update(model.sinteringTemp, dt, ffKiln);

    // Loop 4: Preheater Top Draft
    const idDamperOp = this.picPh.update(model.preheaterTopDraft, dt);

    // Loop 5: Kiln Hood Pressure
    const coolerVentOp = this.picKh.update(model.kilnHoodPress, dt);

    // Loop 6: Kiln Inlet O2
    const tadDamperOp = this.aicO2.update(model.kilnInletO2, dt);

    return {
      feedRate: feedOp,
      pcFuelOp: pcFuelOp,
      kilnFuelOp: kilnFuelOp,
      idFanDamper: idDamperOp,
      coolerVentSpeed: coolerVentOp,
      tadDamper: tadDamperOp
    };
  }
}

// Export for browser global context
window.PyroprocessControlSystem = PyroprocessControlSystem;
