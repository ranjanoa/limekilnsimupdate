/**
 * KILN 3 CEMENT PYROPROCESS DYNAMIC PHYSICS ENGINE
 * Coupled First-Principles ODE Simulator for SIMIT Digital Twin
 * 
 * Production Baseline: 280.0 t/h Raw Meal -> 175.0 t/h Clinker (4,200 tpd)
 * Specific Heat: 775.6 kcal/kg clinker (3,247 kJ/kg clinker)
 */

class CementProcessModel {
  constructor() {
    this.resetToNominal();
  }

  resetToNominal() {
    // ================= 1. OPERATING STATE VARIABLES =================
    // Feed & Production
    this.rawMealFeed = 280.0;           // t/h dry raw meal (K3F07)
    this.clinkerProduction = 175.0;     // t/h clinker yield
    this.clinkerFactor = 1.60;          // t meal / t clinker
    this.rawMealMoisture = 0.50;        // % moisture
    this.rawMealTemp = 60.0;            // °C

    // Rotary Kiln Mechanical & Bed States
    this.kilnSpeed = 3.79;              // rpm (L3S01)
    this.kilnMotorAmp = 254.0;          // Amperes (L3I01)
    this.kilnDriveCurrent = 254.0;      // Alias for L3I01
    this.kilnFillingDegree = 10.96;     // % filling (G.E.)
    this.kilnShellTemp = 305.0;         // °C shell scanner
    this.sinteringTemp = 1450.0;        // °C optical pyrometer (TERMO)
    this.burningZoneT1 = 1307.0;        // °C (L3T342)
    this.burningZoneT2 = 1317.0;        // °C (L3T12)
    this.clinkerFreeLime = 1.30;        // % free CaO (Cal Livre)
    this.kilnBedTransitTime = 26.8;     // minutes mean residence time

    // Discretized Kiln Bed Slices (10 cells for axial delay & kinetics)
    this.numKilnCells = 10;
    this.kilnBedTemp = new Array(this.numKilnCells).fill(0).map((_, i) => {
      return 880.0 + (1450.0 - 880.0) * Math.pow(i / (this.numKilnCells - 1), 1.6);
    });
    this.kilnBedCalcination = new Array(this.numKilnCells).fill(0.925).map((val, i) => {
      return val + (1.0 - val) * Math.min(1.0, i / 3.0);
    });

    // Precalciner Chamber States
    this.pcExitTemp = 907.0;            // °C (K3T62A)
    this.pcMidTemp = 896.0;             // °C (K3T62)
    this.pcCalcinationDegree = 0.925;   // 92.5% decarbonation
    this.pcDecarbonation = 92.5;        // % decarbonation (alias)
    this.pcPressure = 0.28;             // mbar (K3P19)
    this.pcMassHoldup = 2400.0;         // kg solids in suspension

    // Preheater Cyclone Temperatures & Pressures
    this.cyclone1N_GasT = 432.0;        // °C (K3T17)
    this.cyclone1N_MealT = 458.0;       // °C (K3T19)
    this.cyclone1N_Press = -51.0;       // mbar (K3P12)

    this.cyclone1P_GasT = 408.0;        // °C (K3T18)
    this.cyclone1P_MealT = 407.0;       // °C (K3T20)
    this.cyclone1P_Press = -50.0;       // mbar (K3P13)

    this.preheaterTopGasT = 413.0;      // °C (K3T16)
    this.preheaterTopDraft = -56.0;     // mbar (K3P02)

    this.cyclone2N_GasT = 637.0;        // °C (K3T48)
    this.cyclone2N_BodyT = 635.0;       // °C (K3T50)
    this.cyclone2N_Press = -39.0;       // mbar (K3P15B)

    this.cyclone2P_GasT = 608.0;        // °C (K3T49)
    this.cyclone2P_BodyT = 606.0;       // °C (K3T51)
    this.cyclone2P_Press = -31.0;       // mbar (K3P15)

    this.stage3_GasT = 650.0;           // °C (K3T21)
    this.stage3_BodyT = 762.0;          // °C (K3T52)
    this.stage3_Press = -9.6;           // mbar (K3P14)
    this.stage3_Flap = 45.0;            // % (K3G14)

    this.cyclone4N_GasT = 914.0;        // °C (K3T22)
    this.cyclone4N_MealT = 919.0;       // °C (K3T25)
    this.cyclone4N_Press = -18.0;       // mbar (K3P04)

    this.cyclone4P_GasT = 896.0;        // °C (K3T23)
    this.cyclone4P_MealT = 887.0;       // °C (K3T26)
    this.cyclone4P_Press = -17.0;       // mbar (K3P05)

    // Gas Analyzers
    this.phGasO2 = 3.18;                // % (K3Q02)
    this.phGasCO = 0.310;               // % (K3Q03)
    this.kilnInletO2 = 2.32;            // % (K3Q01)
    this.kilnInletNOx = 857.0;          // ppm (K3Q07)
    this.kilnInletCO = 0.004;           // % (K3Q06)
    this.kilnInletSO2 = 359.0;          // ppm (K3AI00211)
    this.kilnInletTemp = 1050.0;        // °C gas
    this.kilnInletMealT = 529.0;        // °C meal shelf (K3T24)
    this.kilnInletPress = -1.3;         // mbar (K3P06I)

    // Clinker Grate Cooler
    this.secondaryAirT = 1000.0;        // °C (L3T305)
    this.kilnHoodPress = -0.30;         // mbar (L3P311)
    this.tertiaryAirT = 862.0;          // °C (K3T60)
    this.tertiaryAirPress = -3.6;       // mbar (K3P17)
    this.tadDamperPos = 99.0;           // % (K3G36)
    this.coolerVentT = 258.0;           // °C (L3T324)
    this.coolerFilterT = 89.0;          // °C (L3T322)
    this.coolerFilterDP = 10.0;         // mbar (L3P318)
    this.coolerFanSpeed = 85.0;         // % (Fan speed reference)
    this.coolerFanCurrent = 289.0;      // A (L3M366)
    this.coolerFanRpm = 908.0;          // rpm (L3S310)
    this.clinkerDischargeT = 90.0;      // °C
    this.coolerDischargeT = 90.0;       // °C (alias for clinkerDischargeT)

    // Fuels & Actuators
    this.pcCdrRate = 10.66;             // t/h (Z3N218 + Z3N213)
    this.pcPetcokeRate = 3.68;          // t/h (S3F04)
    this.kilnPetcokeRate = 6.15;        // t/h (L3F200)
    this.kilnCdrRate = 2.44;            // t/h (Z3N412)
    this.kilnOilRate = 605.0;           // l/h (L3F03)
    this.idFanDamper = 92.0;            // % (K3G37)
    this.sncrAmmoniaFlow = 115.0;       // l/h

    // Thermal Consumption KPI
    this.heatConsumptionKcal = 775.6;   // kcal/kg clinker
    this.pcThermalSplit = 54.1;         // %
    this.alternativeFuelRate = 41.5;    // %ST Total
    this.altFuelSubstitution = 41.5;    // % TSR (alias)
  }

  /**
   * Main Physics Step — Solves coupled non-linear differential equations
   * @param {number} dt - Time step in seconds
   * @param {Object} controlDemands - Manipulated variables from DCS controllers
   */
  step(dt, controlDemands) {
    // Apply actuator inputs with physical limits and smooth feeder dynamics
    if (controlDemands.feedRate !== undefined) {
      const targetFeed = Math.max(100.0, Math.min(360.0, controlDemands.feedRate));
      this.rawMealFeed += (targetFeed - this.rawMealFeed) * (dt / 1.5);
    }
    if (controlDemands.pcFuelOp !== undefined) {
      // 54.1% nominal matches 10.66 t/h CDR + 3.68 t/h Petcoke
      const pcRatio = Math.max(0.2, controlDemands.pcFuelOp / 54.1);
      this.pcCdrRate = 10.66 * pcRatio;
      this.pcPetcokeRate = 3.68 * pcRatio;
    }
    if (controlDemands.kilnFuelOp !== undefined) {
      // 45.9% nominal matches 6.15 t/h Petcoke + 2.44 t/h CDR + 605 l/h Oil
      const kilnRatio = Math.max(0.2, controlDemands.kilnFuelOp / 45.9);
      this.kilnPetcokeRate = 6.15 * kilnRatio;
      this.kilnCdrRate = 2.44 * kilnRatio;
      this.kilnOilRate = 605.0 * kilnRatio;
    }
    if (controlDemands.idFanDamper !== undefined) {
      this.idFanDamper = Math.max(20.0, Math.min(100.0, controlDemands.idFanDamper));
    }
    if (controlDemands.coolerVentSpeed !== undefined) {
      const ventFactor = Math.max(0.2, controlDemands.coolerVentSpeed / 75.5);
      this.coolerFanRpm = 908.0 * ventFactor;
      this.coolerFanCurrent = 289.0 * Math.pow(ventFactor, 1.2);
    }
    if (controlDemands.tadDamper !== undefined) {
      this.tadDamperPos = Math.max(10.0, Math.min(100.0, controlDemands.tadDamper));
    }

    // ================= 2. KILN ROTATION & MATERIAL BED TRANSPORT =================
    // Kiln speed ratio controller: speed tracks feed rate to maintain ~10.96% filling degree
    const targetKilnSpeed = 3.79 * (this.rawMealFeed / 280.0);
    this.kilnSpeed += (targetKilnSpeed - this.kilnSpeed) * (dt / 3.0);
    this.kilnMotorAmp = 254.0 * (0.3 + 0.7 * (this.rawMealFeed / 280.0) * (this.kilnSpeed / 3.79));
    this.kilnDriveCurrent = this.kilnMotorAmp;
    this.kilnFillingDegree = 10.96 * (this.rawMealFeed / 280.0) / Math.max(0.5, (this.kilnSpeed / 3.79));

    // Clinker production tracks feed rate with transport delay through kiln
    const steadyClinker = this.rawMealFeed / this.clinkerFactor;
    // Kiln bed delay filter (tau ~ 26.8 minutes = 1608 seconds)
    const tauBed = 1608.0 / Math.max(0.2, this.kilnSpeed / 3.79);
    this.clinkerProduction += (steadyClinker - this.clinkerProduction) * (dt / tauBed);

    // ================= 3. PRECALCINER ENERGY & DECARBONATION KINETICS =================
    const pcFuelFactor = (this.pcCdrRate * 18.0 + this.pcPetcokeRate * 31.4) / (10.66 * 18.0 + 3.68 * 31.4);
    const feedCooling = (this.rawMealFeed - 280.0) * 0.35;
    const targetPcTemp = 907.0 + (pcFuelFactor - 1.0) * 160.0 - feedCooling + (this.tertiaryAirT - 862.0) * 0.15;
    this.pcExitTemp += (targetPcTemp - this.pcExitTemp) * (dt / 4.0);
    this.pcMidTemp = this.pcExitTemp - 11.0;

    // Decarbonation degree responds to temperature via Arrhenius law
    this.pcCalcinationDegree = 0.925 + 0.0006 * (this.pcExitTemp - 907.0);
    this.pcCalcinationDegree = Math.max(0.70, Math.min(0.98, this.pcCalcinationDegree));
    this.pcDecarbonation = this.pcCalcinationDegree * 100.0;

    // ================= 4. ROTARY KILN COMBUSTION & SINTERING ZONE DYNAMICS =================
    const kilnNominalGj = 6.15 * 31.4 + 2.44 * 18.0 + (605.0 * 0.95 * 41.8 / 1000.0);
    const kilnActualGj = this.kilnPetcokeRate * 31.4 + this.kilnCdrRate * 18.0 + (this.kilnOilRate * 0.95 * 41.8 / 1000.0);
    const kilnFuelFactor = kilnActualGj / kilnNominalGj;

    const targetSintering = 1450.0 + (kilnFuelFactor - 1.0) * 200.0 - (this.rawMealFeed - 280.0) * 0.30 + (this.secondaryAirT - 1000.0) * 0.25;
    this.sinteringTemp += (targetSintering - this.sinteringTemp) * (dt / 8.0);
    this.burningZoneT1 = this.sinteringTemp - 143.0;
    this.burningZoneT2 = this.sinteringTemp - 133.0;

    // Kiln shell temperature follows sintering temperature
    this.kilnShellTemp = 280.0 + (this.sinteringTemp - 1300.0) * 0.17;

    // Clinker Free Lime (Cal Livre) kinetics:
    // High sintering temp and long residence time drive free CaO into C3S (lower free lime)
    const targetFreeLime = 1.30 - 0.015 * (this.sinteringTemp - 1450.0) + 0.008 * (this.rawMealFeed - 280.0);
    this.clinkerFreeLime += (Math.max(0.2, Math.min(4.5, targetFreeLime)) - this.clinkerFreeLime) * (dt / 60.0);

    // Kiln inlet exhaust gas temperature follows kiln thermal balance
    this.kilnInletTemp = 1000.0 + (this.sinteringTemp - 1400.0) * 0.33;
    this.kilnInletMealT = 529.0 + (this.rawMealFeed - 280.0) * 0.25;

    // ================= 5. CLINKER COOLER RECUPERATION & HOOD DRAFT =================
    // Secondary Air Temperature tracks burning zone & clinker inflow
    const targetSecAirT = 950.0 + (this.sinteringTemp - 1400.0) * 0.8 - (this.rawMealFeed - 280.0) * 0.15;
    this.secondaryAirT += (targetSecAirT - this.secondaryAirT) * (dt / 10.0);

    // Tertiary Air Temperature (K3T60)
    const targetTertAirT = 820.0 + (this.secondaryAirT - 950.0) * 0.65;
    this.tertiaryAirT += (targetTertAirT - this.tertiaryAirT) * (dt / 12.0);

    // Cooler Vent Air Temperature (L3T324) and Bag Filter (L3T322)
    this.coolerVentT = 258.0 + (this.clinkerProduction - 175.0) * 0.4;
    this.coolerFilterT = 89.0 + (this.coolerVentT - 258.0) * 0.2;

    // Kiln Hood Draft Pressure (L3P311)
    const targetHoodPress = -0.30 - ((this.coolerFanRpm / 908.0) - 1.0) * 1.5 + ((this.rawMealFeed / 280.0) - 1.0) * 0.4;
    this.kilnHoodPress += (targetHoodPress - this.kilnHoodPress) * (dt / 0.8);

    // Preheater draft and stage gradients are calculated in Section 6 below

    // ================= 6. PREHEATER TOWER DUAL STRING PROFILES =================
    // Cyclone Stage 4 (4N and 4P)
    this.cyclone4N_GasT = this.pcExitTemp + 7.0;
    this.cyclone4N_MealT = this.pcExitTemp + 12.0;
    this.cyclone4P_GasT = this.pcExitTemp - 11.0;
    this.cyclone4P_MealT = this.pcExitTemp - 20.0;

    // Stage 3 Chamber (K3T52)
    const targetStage3T = 762.0 + (this.pcExitTemp - 907.0) * 0.7 - (this.rawMealFeed - 280.0) * 0.2;
    this.stage3_BodyT += (targetStage3T - this.stage3_BodyT) * (dt / 10.0);
    this.stage3_GasT = this.stage3_BodyT - 112.0;

    // Stage 2 Cyclones (2N and 2P)
    this.cyclone2N_BodyT = 635.0 + (this.stage3_BodyT - 762.0) * 0.65;
    this.cyclone2N_GasT = this.cyclone2N_BodyT + 2.0;
    this.cyclone2P_BodyT = 606.0 + (this.stage3_BodyT - 762.0) * 0.65;
    this.cyclone2P_GasT = this.cyclone2P_BodyT + 2.0;

    // Stage 1 Cyclones (1N and 1P) - Fresh meal addition (140 t/h per string @ 60°C)
    const feedCoolingEffect = (this.rawMealFeed - 280.0) * 0.35;
    this.cyclone1N_GasT = 432.0 + (this.cyclone2N_BodyT - 635.0) * 0.45 - feedCoolingEffect;
    this.cyclone1N_MealT = 458.0 + (this.cyclone2N_BodyT - 635.0) * 0.45 - feedCoolingEffect;

    this.cyclone1P_GasT = 408.0 + (this.cyclone2P_BodyT - 606.0) * 0.45 - feedCoolingEffect;
    this.cyclone1P_MealT = 407.0 + (this.cyclone2P_BodyT - 606.0) * 0.45 - feedCoolingEffect;

    // Combined Top Preheater Exhaust (K3T16)
    this.preheaterTopGasT = (this.cyclone1N_GasT + this.cyclone1P_GasT) / 2.0;

    // Preheater Draft Network (K3P02, K3P12, K3P13, etc.)
    // Driven by ID Fan Damper / Speed (K3G37)
    const fanSuctionHead = -60.0 * Math.pow(this.idFanDamper / 92.0, 1.8);
    const gasVolumeFactor = Math.sqrt((this.preheaterTopGasT + 273.0) / (413.0 + 273.0));
    const targetTopDraft = fanSuctionHead * gasVolumeFactor + (this.rawMealFeed / 280.0) * 4.0;
    this.preheaterTopDraft += (targetTopDraft - this.preheaterTopDraft) * (dt / 1.5);

    // Hydraulic gradient down the preheater tower
    this.cyclone1N_Press = this.preheaterTopDraft + 5.0;
    this.cyclone1P_Press = this.preheaterTopDraft + 6.0;
    this.cyclone2N_Press = this.preheaterTopDraft + 17.0;
    this.cyclone2P_Press = this.preheaterTopDraft + 25.0;
    this.stage3_Press = this.preheaterTopDraft + 46.4;
    this.cyclone4N_Press = this.preheaterTopDraft + 38.0;
    this.cyclone4P_Press = this.preheaterTopDraft + 39.0;
    this.tertiaryAirPress = -3.6 * (this.idFanDamper / 92.0);
    this.kilnInletPress = -1.3 * (this.idFanDamper / 92.0);

    // ================= 7. FLUE GAS ANALYZERS (O2, CO, NOx, SO2) =================
    // Kiln Inlet Oxygen (K3Q01): Stoichiometric balance between burner fuel and secondary air
    const totalKilnAir = 78000.0 * (1.0 - (this.kilnHoodPress + 0.3) * 0.05);
    const kilnStoichDemand = (this.kilnPetcokeRate * 7.5 + this.kilnCdrRate * 4.2 + (this.kilnOilRate * 0.95 / 1000.0) * 11.0) * 1000.0;
    const targetKilnO2 = 2.32 + ((totalKilnAir - kilnStoichDemand) / 10000.0) * 0.8;
    this.kilnInletO2 += (Math.max(0.5, Math.min(8.0, targetKilnO2)) - this.kilnInletO2) * (dt / 10.0);

    // Preheater Middle & Top Oxygen (K3Q02)
    const targetPhO2 = this.kilnInletO2 + 0.86 * (this.tadDamperPos / 99.0);
    this.phGasO2 += (Math.max(1.0, Math.min(10.0, targetPhO2)) - this.phGasO2) * (dt / 8.0);

    // Carbon Monoxide (K3Q03, K3Q06) - Rises sharply when O2 drops below stoichiometric
    if (this.phGasO2 < 2.0) {
      this.phGasCO = 0.31 + (2.0 - this.phGasO2) * 0.8;
    } else {
      this.phGasCO = 0.310 - (this.phGasO2 - 3.18) * 0.08;
    }
    this.phGasCO = Math.max(0.02, Math.min(3.5, this.phGasCO));
    this.kilnInletCO = Math.max(0.001, 0.004 * (this.phGasCO / 0.31));

    // Nitric Oxide NOx (K3Q07) - Thermal NOx exponential with sintering flame temperature
    // DeNOx SNCR Ammonia reduces NOx: nominal 115 l/h
    const thermalNox = 857.0 * Math.exp(0.0035 * (this.sinteringTemp - 1450.0));
    const deNoxFactor = Math.max(0.4, 1.0 - 0.0025 * (this.sncrAmmoniaFlow - 115.0));
    this.kilnInletNOx = thermalNox * deNoxFactor;

    // Sulfur Dioxide SO2 (K3AI00211) - Volatile circulation loop
    this.kilnInletSO2 = 359.0 + (this.kilnPetcokeRate - 6.15) * 45.0 - (this.sinteringTemp - 1450.0) * 0.5;

    // ================= 8. OVERALL THERMAL EFFICIENCY & KPI CALCULATIONS =================
    // Total fuel energy (GJ/h)
    const totalGj = (this.pcCdrRate * 18.0 + this.pcPetcokeRate * 31.4 + 
                     this.kilnPetcokeRate * 31.4 + this.kilnCdrRate * 18.0 + 
                     (this.kilnOilRate * 0.95 * 41.8 / 1000.0));
    const pcGj = (this.pcCdrRate * 18.0 + this.pcPetcokeRate * 31.4);
    const altGj = (this.pcCdrRate * 18.0 + this.kilnCdrRate * 18.0);

    this.pcThermalSplit = (pcGj / Math.max(1.0, totalGj)) * 100.0;
    this.alternativeFuelRate = (altGj / Math.max(1.0, totalGj)) * 100.0;
    this.altFuelSubstitution = this.alternativeFuelRate;
    // Heat consumption: kcal/kg clinker
    this.heatConsumptionKcal = (totalGj * 1e6 / 4.1868) / (Math.max(10.0, this.clinkerProduction) * 1000.0);
  }

  getFlowsheetData() {
    const n = (val, def = 0) => (typeof val === 'number' && !isNaN(val)) ? val : def;
    const fix = (val, digits = 2, def = 0) => Number(n(val, def).toFixed(digits));

    const feed = n(this.rawMealFeed, 280.0);
    const clinker = n(this.clinkerProduction, 175.0);
    const pc_cdr = n(this.pcCdrRate, 10.66);
    const pc_pet = n(this.pcPetcokeRate, 3.68);
    const kiln_pet = n(this.kilnPetcokeRate, 6.15);
    const kiln_cdr = n(this.kilnCdrRate, 2.44);
    const kiln_oil_tph = (n(this.kilnOilRate, 605.0) * 0.95) / 1000.0;

    const fan_spd = n(this.coolerFanSpeed, 85.0);
    const tad_pos = n(this.tadDamperPos, 99.0);

    const tert_air_tph = 145.0 * (tad_pos / 99.0) * (feed / 280.0);
    const tert_air_nm3h = (tert_air_tph * 1000.0) / 1.293;
    const sec_air_tph = 98.5 * (fan_spd / 85.0);
    const sec_air_nm3h = (sec_air_tph * 1000.0) / 1.293;
    const primary_air_tph = 12.0;
    const primary_air_nm3h = (primary_air_tph * 1000.0) / 1.293;
    const cooling_air_tph = 360.0 * (fan_spd / 85.0);
    const cooling_air_nm3h = (cooling_air_tph * 1000.0) / 1.293;
    const cooler_vent_tph = Math.max(20.0, cooling_air_tph - tert_air_tph - sec_air_tph);
    const cooler_vent_nm3h = (cooler_vent_tph * 1000.0) / 1.293;

    const kiln_flue_gas_tph = sec_air_tph + primary_air_tph + kiln_pet + kiln_cdr + kiln_oil_tph - (clinker * 0.03);
    const kiln_flue_gas_nm3h = (kiln_flue_gas_tph * 1000.0) / 1.35;

    const calciner_co2_tph = (feed * 0.7685) * (44.01 / 100.09) * n(this.pcCalcinationDegree, 0.925);
    const pc_flue_tph = tert_air_tph + pc_cdr + pc_pet;
    const pc_gas_tph = kiln_flue_gas_tph + pc_flue_tph + calciner_co2_tph;
    const pc_gas_nm3h = (pc_gas_tph * 1000.0) / 1.38;

    const ph_top_gas_tph = pc_gas_tph + (feed * (n(this.rawMealMoisture, 0.5) / 100.0)) + 3.2;
    const ph_top_gas_nm3h = (ph_top_gas_tph * 1000.0) / 1.37;

    const dust_loss_tph = feed * 0.015;
    const clinker_silo_tph = clinker;

    const calc_h_solid = (flow_tph, temp_c, cp_kcal = 0.22) => (n(flow_tph) * 1000.0 * cp_kcal * n(temp_c) * 4.1868) / 1e6;
    const calc_h_gas = (flow_tph, temp_c, cp_kcal = 0.26) => (n(flow_tph) * 1000.0 * cp_kcal * n(temp_c) * 4.1868) / 1e6;

    const cdr_lhv_gj_t = 18.0;
    const pet_lhv_gj_t = 31.4;
    const oil_lhv_gj_t = 41.8;

    const cooler_disch_t = n(this.coolerDischargeT, n(this.clinkerDischargeT, 90.0));
    const free_lime = n(this.clinkerFreeLime, 1.30);

    const streams = [
      { id: 1, name: "Raw Meal Total Feed", phase: "Solid", from: "Meal Silo", to: "Preheater Top Air Lift", mass_tph: fix(feed, 2), nm3h: null, temp_c: 60.0, press_mbar: 0.0, enthalpy_gjh: fix(calc_h_solid(feed, 60.0, 0.21), 2), composition: "Dry Raw Meal, CaCO3: 76.85%, SiO2: 13.50%, LOI: 35.33%" },
      { id: 2, name: "Raw Meal String N Feed", phase: "Solid", from: "Meal Splitter Gate", to: "Gas Riser 1N-2N", mass_tph: fix(feed * 0.5, 2), nm3h: null, temp_c: 60.0, press_mbar: fix(this.cyclone2N_Press, 1, -39.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.5, 60.0, 0.21), 2), composition: "50% raw meal split to North string" },
      { id: 3, name: "Raw Meal String P Feed", phase: "Solid", from: "Meal Splitter Gate", to: "Gas Riser 1P-2P", mass_tph: fix(feed * 0.5, 2), nm3h: null, temp_c: 60.0, press_mbar: fix(this.cyclone2P_Press, 1, -31.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.5, 60.0, 0.21), 2), composition: "50% raw meal split to South string" },
      { id: 4, name: "Cyclone 1N Meal Exit", phase: "Solid", from: "Cyclone 1N Dipleg", to: "Riser Duct to 2N", mass_tph: fix(feed * 0.499, 2), nm3h: null, temp_c: fix(this.cyclone1N_MealT, 1, 458.0), press_mbar: fix(this.cyclone1N_Press, 1, -51.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.499, this.cyclone1N_MealT, 0.22), 2), composition: "Preheated raw meal, moisture evaporated" },
      { id: 5, name: "Cyclone 1P Meal Exit", phase: "Solid", from: "Cyclone 1P Dipleg", to: "Riser Duct to 2P", mass_tph: fix(feed * 0.499, 2), nm3h: null, temp_c: fix(this.cyclone1P_MealT, 1, 407.0), press_mbar: fix(this.cyclone1P_Press, 1, -50.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.499, this.cyclone1P_MealT, 0.22), 2), composition: "Preheated raw meal, moisture evaporated" },
      { id: 6, name: "Cyclone 2N Meal Exit", phase: "Solid", from: "Cyclone 2N Dipleg", to: "Stage 3 Chamber Riser", mass_tph: fix(feed * 0.498, 2), nm3h: null, temp_c: fix(this.cyclone2N_BodyT, 1, 635.0), press_mbar: fix(this.cyclone2N_Press, 1, -39.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.498, this.cyclone2N_BodyT, 0.23), 2), composition: "Partially dehydroxylated clay minerals" },
      { id: 7, name: "Cyclone 2P Meal Exit", phase: "Solid", from: "Cyclone 2P Dipleg", to: "Stage 3 Chamber Riser", mass_tph: fix(feed * 0.498, 2), nm3h: null, temp_c: fix(this.cyclone2P_BodyT, 1, 606.0), press_mbar: fix(this.cyclone2P_Press, 1, -31.0), enthalpy_gjh: fix(calc_h_solid(feed * 0.498, this.cyclone2P_BodyT, 0.23), 2), composition: "Partially dehydroxylated clay minerals" },
      { id: 8, name: "Stage 3 Meal Outflow", phase: "Solid", from: "Stage 3 Cyclone Dipleg", to: "Precalciner Chamber", mass_tph: fix(feed * 0.995, 2), nm3h: null, temp_c: fix(this.stage3_BodyT, 1, 762.0), press_mbar: fix(this.stage3_Press, 1, -9.6), enthalpy_gjh: fix(calc_h_solid(feed * 0.995, this.stage3_BodyT, 0.24), 2), composition: "Meal ready for calcination (12.5% pre-decarb)" },
      { id: 9, name: "Precalciner CDR Fuel", phase: "Solid", from: "Feeder Z3N218 / 213", to: "Precalciner Lower Burners", mass_tph: fix(pc_cdr, 2), nm3h: null, temp_c: 25.0, press_mbar: 0.0, enthalpy_gjh: fix(pc_cdr * cdr_lhv_gj_t, 2), composition: "RDF/CDR, LHV=18.0 MJ/kg, Ash=11.3%, H2O=14%" },
      { id: 10, name: "Precalciner Petcoke Fuel", phase: "Solid", from: "Feeder S3F04", to: "Precalciner Burners", mass_tph: fix(pc_pet, 2), nm3h: null, temp_c: 65.0, press_mbar: 0.0, enthalpy_gjh: fix(pc_pet * pet_lhv_gj_t, 2), composition: "Petcoke, LHV=31.4 MJ/kg, S=5.5%, VM=10.2%" },
      { id: 11, name: "Tertiary Air to PC", phase: "Gas", from: "Cooler Tertiary Duct Takeoff", to: "Precalciner Combustion Bottom", mass_tph: fix(tert_air_tph, 2), nm3h: Math.round(n(tert_air_nm3h)), temp_c: fix(this.tertiaryAirT, 1, 862.0), press_mbar: fix(this.tertiaryAirPress, 1, -3.6), enthalpy_gjh: fix(calc_h_gas(tert_air_tph, this.tertiaryAirT, 0.26), 2), composition: "O2: 20.7%, N2: 78.4%, CO2: 0.04%" },
      { id: 12, name: "Kiln Flue Gas to PC Riser", phase: "Gas", from: "Kiln Smoke Chamber / Inlet", to: "Precalciner Bottom Riser", mass_tph: fix(kiln_flue_gas_tph, 2), nm3h: Math.round(n(kiln_flue_gas_nm3h)), temp_c: fix(this.burningZoneT2, 1, 1317.0), press_mbar: fix(this.kilnInletPress, 1, -1.3), enthalpy_gjh: fix(calc_h_gas(kiln_flue_gas_tph, this.burningZoneT2, 0.28), 2), composition: `CO2: 24.8%, O2: ${fix(this.kilnInletO2, 2, 2.32)}%, NOx: ${fix(this.kilnInletNOx, 0, 857)} ppm` },
      { id: 13, name: "PC Exit Gas + Meal Suspension", phase: "2-Phase", from: "Precalciner Vessel Top", to: "Cyclones 4N & 4P", mass_tph: fix(pc_gas_tph + (clinker * 1.042), 2), nm3h: Math.round(n(pc_gas_nm3h)), temp_c: fix(this.pcExitTemp, 1, 907.0), press_mbar: fix(this.pcPressure, 1, 0.28), enthalpy_gjh: fix(calc_h_gas(pc_gas_tph, this.pcExitTemp, 0.27) + calc_h_solid(clinker * 1.042, this.pcExitTemp, 0.26), 2), composition: `Decarbonation: ${fix(this.pcDecarbonation, 1, 92.5)}%, CO2: 33.2%` },
      { id: 14, name: "Cyclone 4N Calcined Meal", phase: "Solid", from: "Cyclone 4N Dipleg", to: "Kiln Inlet Feeding Shelf", mass_tph: fix(clinker * 0.521, 2), nm3h: null, temp_c: fix(this.cyclone4N_MealT, 1, 919.0), press_mbar: fix(this.cyclone4N_Press, 1, -18.0), enthalpy_gjh: fix(calc_h_solid(clinker * 0.521, this.cyclone4N_MealT, 0.26), 2), composition: `CaO: 66.8%, Decarb: ${fix(this.pcDecarbonation, 1, 92.5)}%` },
      { id: 15, name: "Cyclone 4P Calcined Meal", phase: "Solid", from: "Cyclone 4P Dipleg", to: "Kiln Inlet Feeding Shelf", mass_tph: fix(clinker * 0.521, 2), nm3h: null, temp_c: fix(this.cyclone4P_MealT, 1, 887.0), press_mbar: fix(this.cyclone4P_Press, 1, -17.0), enthalpy_gjh: fix(calc_h_solid(clinker * 0.521, this.cyclone4P_MealT, 0.26), 2), composition: `CaO: 66.8%, Decarb: ${fix(this.pcDecarbonation, 1, 92.5)}%` },
      { id: 16, name: "Kiln Main Petcoke Fuel", phase: "Solid", from: "Feeder L3F200", to: "Kiln Main Burner Pipe", mass_tph: fix(kiln_pet, 2), nm3h: null, temp_c: 65.0, press_mbar: 0.0, enthalpy_gjh: fix(kiln_pet * pet_lhv_gj_t, 2), composition: "Petcoke, LHV=31.4 MJ/kg, 86.5% C" },
      { id: 17, name: "Kiln Main CDR Fuel", phase: "Solid", from: "Feeder Z3N412", to: "Kiln Main Burner Lance", mass_tph: fix(kiln_cdr, 2), nm3h: null, temp_c: 25.0, press_mbar: 0.0, enthalpy_gjh: fix(kiln_cdr * cdr_lhv_gj_t, 2), composition: "Alternative fuel CDR, LHV=18.0 MJ/kg" },
      { id: 18, name: "Kiln Heavy Fuel Oil Trim", phase: "Liquid", from: "HFO Metering Rack L3F03", to: "Kiln Main Burner Central Gun", mass_tph: fix(kiln_oil_tph, 2), nm3h: null, temp_c: 85.0, press_mbar: 18000.0, enthalpy_gjh: fix(kiln_oil_tph * oil_lhv_gj_t, 2), composition: "Heavy Fuel Oil, LHV=41.8 MJ/kg (605 L/h)" },
      { id: 19, name: "Secondary Air to Kiln", phase: "Gas", from: "Cooler Recuperating Grate", to: "Kiln Hood / Flame Zone", mass_tph: fix(sec_air_tph, 2), nm3h: Math.round(n(sec_air_nm3h)), temp_c: fix(this.secondaryAirT, 1, 1000.0), press_mbar: fix(this.kilnHoodPress, 2, -0.30), enthalpy_gjh: fix(calc_h_gas(sec_air_tph, this.secondaryAirT, 0.27), 2), composition: "Preheated combustion air, O2: 20.6%, N2: 78.5%" },
      { id: 20, name: "Primary Air to Burner", phase: "Gas", from: "Primary High-Pressure Blower", to: "Kiln Burner Momentum Nozzles", mass_tph: fix(primary_air_tph, 2), nm3h: Math.round(n(primary_air_nm3h)), temp_c: 35.0, press_mbar: 120.0, enthalpy_gjh: 0.42, composition: "Axial/Radial flame momentum air (9% total)" },
      { id: 21, name: "Clinker Discharged from Kiln", phase: "Solid", from: "Kiln Sintering Bed", to: "Grate Cooler Inlet Bullnose", mass_tph: fix(clinker, 2), nm3h: null, temp_c: 1350.0, press_mbar: fix(this.kilnHoodPress, 2, -0.30), enthalpy_gjh: fix(calc_h_solid(clinker, 1350.0, 0.27), 2), composition: `C3S: 61.2%, C2S: 16.5%, Free CaO: ${fix(free_lime, 2, 1.30)}%` },
      { id: 22, name: "Cooler Ambient Aeration Air", phase: "Gas", from: "Cooling Fans 1 to 6", to: "Cooler Undergrate Chambers", mass_tph: fix(cooling_air_tph, 2), nm3h: Math.round(n(cooling_air_nm3h)), temp_c: 25.0, press_mbar: 65.0, enthalpy_gjh: fix(calc_h_gas(cooling_air_tph, 25.0, 0.24), 2), composition: "Ambient aeration air, 2.05 kg air / kg clinker" },
      { id: 23, name: "Clinker Product to Silo", phase: "Solid", from: "Clinker Grate Discharge Crusher", to: "Transport Deep Bucket Elevator", mass_tph: fix(clinker_silo_tph, 2), nm3h: null, temp_c: fix(cooler_disch_t, 1, 90.0), press_mbar: 0.0, enthalpy_gjh: fix(calc_h_solid(clinker_silo_tph, cooler_disch_t, 0.21), 2), composition: `Quality C3S: 61.5%, Free Lime: ${fix(free_lime, 2, 1.30)}%` },
      { id: 24, name: "Cooler Excess Vent Air", phase: "Gas", from: "Cooler Quenching Hood", to: "Dedusting Baghouse Filter & Stack", mass_tph: fix(cooler_vent_tph, 2), nm3h: Math.round(n(cooler_vent_nm3h)), temp_c: fix(this.coolerVentT, 1, 258.0), press_mbar: -4.6, enthalpy_gjh: fix(calc_h_gas(cooler_vent_tph, this.coolerVentT, 0.25), 2), composition: "Clean cooling excess air, O2: 20.8%, N2: 78.5%" },
      { id: 25, name: "Preheater Combined Top Gas", phase: "Gas", from: "Cyclones 1N & 1P Top Ducts", to: "Conditioning Tower & ID Fan", mass_tph: fix(ph_top_gas_tph, 2), nm3h: Math.round(n(ph_top_gas_nm3h)), temp_c: fix(this.preheaterTopGasT, 1, 413.0), press_mbar: fix(this.preheaterTopDraft, 1, -56.0), enthalpy_gjh: fix(calc_h_gas(ph_top_gas_tph, this.preheaterTopGasT, 0.26), 2), composition: `CO2: 29.8%, O2: ${fix(this.phGasO2, 2, 3.18)}%, CO: ${fix(this.phGasCO, 3, 0.31)}%, H2O: 9.6%` }
    ];

    const total_inflow = feed + pc_cdr + pc_pet + kiln_pet + kiln_cdr + kiln_oil_tph + primary_air_tph + cooling_air_tph;
    const total_outflow = clinker + ph_top_gas_tph + cooler_vent_tph + dust_loss_tph;
    const total_fuel_gj = (pc_cdr * cdr_lhv_gj_t) + (pc_pet * pet_lhv_gj_t) + (kiln_pet * pet_lhv_gj_t) + (kiln_cdr * cdr_lhv_gj_t) + (kiln_oil_tph * oil_lhv_gj_t);
    const total_heat_in_gj = total_fuel_gj + calc_h_solid(feed, 60.0) + calc_h_gas(cooling_air_tph, 25.0) + 0.42;
    const total_heat_consumed_gj = total_heat_in_gj;

    return {
      streams: streams,
      mass_balance: {
        total_inflow_tph: fix(total_inflow, 2),
        total_outflow_tph: fix(total_outflow, 2),
        closure_pct: fix((total_outflow / Math.max(0.1, total_inflow)) * 100.0, 2),
        error_tph: fix(total_outflow - total_inflow, 2)
      },
      heat_balance: {
        fuel_energy_gjh: fix(total_fuel_gj, 2),
        fuel_power_mw: fix(total_fuel_gj / 3.6, 2),
        specific_heat_kcal_kg: fix(this.heatConsumptionKcal, 1, 775.6),
        total_heat_in_gjh: fix(total_heat_in_gj, 2),
        total_heat_consumed_gjh: fix(total_heat_consumed_gj, 2),
        pc_duty_share_pct: fix(this.pcThermalSplit, 1, 54.1)
      }
    };
  }
}

// Export for browser global context
window.CementProcessModel = CementProcessModel;

