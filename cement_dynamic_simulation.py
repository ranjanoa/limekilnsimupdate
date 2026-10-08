"""
KILN 3 CEMENT PYROPROCESSING DYNAMIC SIMULATOR (OFFLINE ENGINE)
Siemens SIMIT Process Model & Non-Linear ODE Solver

Baseline Production:
- Raw Meal Feed Rate: 280.0 t/h (dry basis)
- Clinker Production: 175.0 t/h (4,200 metric tons/day)
- Specific Thermal Consumption: 775.6 kcal/kg clinker (3,247 kJ/kg clinker)
- Thermal Split: 54.1% Precalciner / 45.9% Kiln Main Burner
- Alternative Fuel Substitution (%ST): 41.5% CDR (Refuse Derived Fuel)
"""

import sys
import math
import csv
import time

class PIDController:
    def __init__(self, name, kp, ti, td=0.0, sp=0.0, out_min=0.0, out_max=100.0, reverse=False):
        self.name = name
        self.kp = kp
        self.ti = ti
        self.td = td
        self.sp = sp
        self.pv = sp
        self.op = 50.0
        self.out_min = out_min
        self.out_max = out_max
        self.reverse = reverse
        self.integral = self.op
        self.last_pv = sp

    def update(self, pv, dt, feedforward=0.0):
        self.pv = pv
        error = (self.pv - self.sp) if self.reverse else (self.sp - self.pv)
        
        # Proportional
        p_term = self.kp * error
        
        # Integral with trapezoidal integration & anti-windup clamp
        if self.ti > 0.0:
            self.integral += (self.kp / self.ti) * error * dt
            self.integral = max(self.out_min, min(self.out_max, self.integral))
            
        # Derivative on PV
        d_term = 0.0
        if self.td > 0.0 and dt > 0.0:
            dpv = (self.pv - self.last_pv) / dt
            d_term = -self.kp * self.td * dpv
            
        raw_op = p_term + self.integral + d_term + feedforward
        self.op = max(self.out_min, min(self.out_max, raw_op))
        self.last_pv = pv
        return self.op

class CementPlantSimulation:
    def __init__(self):
        # 1. Operating States
        self.raw_meal_feed = 280.0       # t/h (K3F07)
        self.clinker_production = 175.0  # t/h clinker
        self.clinker_factor = 1.60       # t meal / t clinker
        
        # Rotary Kiln States
        self.kiln_speed = 3.79           # rpm (L3S01)
        self.kiln_amps = 254.0           # A (L3I01)
        self.filling_degree = 10.96      # % (G.E.)
        self.sintering_temp = 1450.0     # °C (TERMO)
        self.free_lime = 1.30            # % CaO (Cal Livre)
        self.kiln_inlet_temp = 1050.0    # °C
        self.kiln_inlet_press = -1.3     # mbar (K3P06I)
        self.kiln_inlet_o2 = 2.32        # % (K3Q01)
        self.kiln_inlet_nox = 857.0      # ppm (K3Q07)
        self.kiln_inlet_co = 0.004       # % (K3Q06)
        
        # Precalciner States
        self.pc_temp = 907.0             # °C (K3T62A)
        self.pc_calcination = 0.925      # 92.5% decarbonated
        self.pc_press = 0.28             # mbar (K3P19)
        self.tertiary_air_temp = 862.0   # °C (K3T60)
        self.tertiary_air_press = -3.6   # mbar (K3P17)
        
        # Preheater Tower States
        self.ph_top_gas_t = 413.0        # °C (K3T16)
        self.ph_top_draft = -56.0        # mbar (K3P02)
        self.cyclone1N_gas_t = 432.0     # °C (K3T17)
        self.cyclone1P_gas_t = 408.0     # °C (K3T18)
        self.cyclone2N_t = 635.0         # °C (K3T50)
        self.cyclone2P_t = 606.0         # °C (K3T51)
        self.stage3_t = 762.0            # °C (K3T52)
        self.cyclone4N_t = 914.0         # °C (K3T22)
        self.cyclone4P_t = 896.0         # °C (K3T23)
        self.ph_o2 = 3.18                # % (K3Q02)
        self.ph_co = 0.310               # % (K3Q03)
        
        # Clinker Grate Cooler
        self.secondary_air_t = 1000.0    # °C (L3T305)
        self.kiln_hood_press = -0.30     # mbar (L3P311)
        self.cooler_vent_t = 258.0       # °C (L3T324)
        self.cooler_filter_t = 89.0      # °C (L3T322)
        self.cooler_fan_current = 289.0  # A (L3M366)
        self.cooler_fan_rpm = 908.0      # rpm (L3S310)
        
        # Fuels
        self.pc_cdr_rate = 10.66         # t/h CDR
        self.pc_petcoke_rate = 3.68      # t/h Petcoke
        self.kiln_petcoke_rate = 6.15    # t/h Petcoke
        self.kiln_cdr_rate = 2.44        # t/h CDR
        self.kiln_oil_rate = 605.0       # l/h Heavy Oil
        
        # Actuators
        self.id_fan_damper = 92.0        # % (K3G37)
        self.cooler_vent_speed = 75.5    # %
        self.tad_damper = 99.0           # % (K3G36)

    def step(self, dt, control_actions):
        # 1. Apply DCS Actuator Demands
        self.raw_meal_feed = max(100.0, min(360.0, control_actions.get('feed_rate', self.raw_meal_feed)))
        
        pc_fuel_ratio = control_actions.get('pc_fuel_op', 54.1) / 54.1
        self.pc_cdr_rate = 10.66 * pc_fuel_ratio
        self.pc_petcoke_rate = 3.68 * pc_fuel_ratio
        
        kiln_fuel_ratio = control_actions.get('kiln_fuel_op', 45.9) / 45.9
        self.kiln_petcoke_rate = 6.15 * kiln_fuel_ratio
        self.kiln_cdr_rate = 2.44 * kiln_fuel_ratio
        self.kiln_oil_rate = 605.0 * kiln_fuel_ratio
        
        self.id_fan_damper = max(20.0, min(100.0, control_actions.get('id_fan_damper', self.id_fan_damper)))
        self.cooler_vent_speed = max(20.0, min(100.0, control_actions.get('cooler_vent_speed', self.cooler_vent_speed)))
        
        # 2. Kiln Speed & Solids Transit
        target_speed = 3.79 * (self.raw_meal_feed / 280.0)
        self.kiln_speed += (target_speed - self.kiln_speed) * (dt / 8.0)
        self.kiln_amps = 254.0 * (0.3 + 0.7 * (self.raw_meal_feed / 280.0))
        self.filling_degree = 10.96 * (self.raw_meal_feed / 280.0) / max(0.5, (self.kiln_speed / 3.79))
        
        steady_clinker = self.raw_meal_feed / self.clinker_factor
        tau_bed = 1608.0 / max(0.2, (self.kiln_speed / 3.79))
        self.clinker_production += (steady_clinker - self.clinker_production) * (dt / tau_bed)
        
        # 3. Precalciner Energy & Decarbonation
        q_pc_fuel = (self.pc_cdr_rate * 18000.0 + self.pc_petcoke_rate * 31400.0) / 3600.0 # MW
        q_calc_sink = (self.raw_meal_feed * 0.7685 * 0.925 * 1782.0 * 1000.0) / 3600000.0 # MW
        q_net_pc = q_pc_fuel - q_calc_sink + 50.0
        target_pc_temp = 800.0 + (q_net_pc / 35.0) * 107.0
        self.pc_temp += (target_pc_temp - self.pc_temp) * (dt / 12.0)
        
        # 4. Sintering Zone Pyrometer & Free Lime Kinetics
        q_kiln_fuel = (self.kiln_petcoke_rate * 31400.0 + self.kiln_cdr_rate * 18000.0 + self.kiln_oil_rate * 0.95 * 41.8) / 3600.0
        target_sinter = 1300.0 + (q_kiln_fuel / 72.46) * 150.0
        self.sintering_temp += (target_sinter - self.sintering_temp) * (dt / 35.0)
        
        target_free_lime = 1.30 - 0.015 * (self.sintering_temp - 1450.0) + 0.008 * (self.raw_meal_feed - 280.0)
        self.free_lime += (max(0.2, min(4.5, target_free_lime)) - self.free_lime) * (dt / 600.0)
        
        # 5. Clinker Cooler & Secondary Air
        target_sec_air = 950.0 + (self.sintering_temp - 1400.0) * 0.8
        self.secondary_air_t += (target_sec_air - self.secondary_air_t) * (dt / 15.0)
        self.tertiary_air_temp = 820.0 + (self.secondary_air_t - 950.0) * 0.65
        
        # Hood Draft Pressure
        air_surplus = 147000.0 * (self.raw_meal_feed / 280.0) - (self.cooler_vent_speed / 75.5) * 147000.0
        target_hood_p = -0.30 + (air_surplus / 10000.0) * 0.5
        self.kiln_hood_press += (target_hood_p - self.kiln_hood_press) * (dt / 1.0)
        
        # 6. Preheater Draft & Temperatures
        target_top_draft = -60.0 * math.pow(self.id_fan_damper / 92.0, 1.8) + (self.raw_meal_feed / 280.0) * 4.0
        self.ph_top_draft += (target_top_draft - self.ph_top_draft) * (dt / 1.5)
        
        self.ph_top_gas_t = 413.0 + (self.pc_temp - 907.0) * 0.35 - (self.raw_meal_feed - 280.0) * 0.35
        self.cyclone1N_gas_t = self.ph_top_gas_t + 19.0
        self.cyclone1P_gas_t = self.ph_top_gas_t - 5.0
        self.stage3_t = 762.0 + (self.pc_temp - 907.0) * 0.7
        self.cyclone4N_t = self.pc_temp + 7.0
        self.cyclone4P_t = self.pc_temp - 11.0
        
        # 7. Gas Analyzers
        target_kln_o2 = 2.32 - (self.kiln_petcoke_rate - 6.15) * 0.35 + (self.secondary_air_t - 1000.0) * 0.005
        self.kiln_inlet_o2 += (max(0.5, min(8.0, target_kln_o2)) - self.kiln_inlet_o2) * (dt / 10.0)
        self.ph_o2 = self.kiln_inlet_o2 + 0.86


def run_dynamic_test():
    print("=" * 75)
    print("KILN 3 CEMENT PYROPROCESS DYNAMIC SIMULATOR (SIMIT MODEL BENCHMARK)")
    print("Nominal Feed: 280.0 t/h | Clinker: 175.0 t/h | Cons: 775.6 kcal/kg")
    print("=" * 75)
    
    plant = CementPlantSimulation()
    
    # Setup DCS PID Controllers
    fic_feed = PIDController("FIC-FEED", kp=1.0, ti=10.0, sp=280.0, out_min=150.0, out_max=350.0)
    fic_feed.op = 280.0
    fic_feed.integral = 280.0
    tic_pc = PIDController("TIC-PC", kp=0.25, ti=20.0, td=2.0, sp=907.0, out_min=20.0, out_max=100.0)
    tic_pc.op = 54.1
    tic_pc.integral = 54.1
    tic_bz = PIDController("TIC-BZ", kp=0.15, ti=35.0, td=3.0, sp=1450.0, out_min=15.0, out_max=90.0)
    tic_bz.op = 45.9
    tic_bz.integral = 45.9
    pic_ph = PIDController("PIC-PH", kp=1.2, ti=6.0, sp=-56.0, out_min=20.0, out_max=100.0, reverse=True)
    pic_ph.op = 92.0
    pic_ph.integral = 92.0
    pic_kh = PIDController("PIC-KH", kp=25.0, ti=3.0, sp=-0.30, out_min=20.0, out_max=100.0, reverse=True)
    pic_kh.op = 75.5
    pic_kh.integral = 75.5
    
    # Simulation settings
    total_sim_time = 600.0 # 10 minutes simulated
    dt = 0.5               # 0.5s step
    time_steps = int(total_sim_time / dt)
    
    # Open CSV for trajectory output
    csv_file = "simulation_test_results.csv"
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time_s", "FeedRate_tph", "Clinker_tph", "KilnSpeed_rpm", 
            "SinteringTemp_C", "PCTemp_C", "FreeLime_pct", 
            "PHTopDraft_mbar", "KilnHood_mbar", "KilnInletO2_pct", 
            "PC_Fuel_OP", "Kiln_Fuel_OP"
        ])
        
        print(f"\nStarting simulation: {total_sim_time}s with dt={dt}s...")
        print(f"{'Time':>6} | {'Feed':>7} | {'Clinker':>7} | {'Speed':>6} | {'Sinter':>7} | {'PC Temp':>7} | {'CaO Free':>8} | {'Hood P':>7}")
        print("-" * 75)
        
        for step_idx in range(time_steps):
            t = step_idx * dt
            
            # Step Disturbance test: At t = 180s, raw meal feed setpoint steps +10% (280 -> 308 t/h)
            if t == 180.0:
                fic_feed.sp = 308.0
                print(f"--> [t={t:.0f}s] INJECTED DISTURBANCE: Raw Meal Feed Setpoint stepped to 308.0 t/h (+10%)")
                
            # Controller execution
            op_feed = fic_feed.sp
            fic_feed.op = op_feed
            fic_feed.pv = plant.raw_meal_feed
            
            # Feedforward trim on fuel loops
            ff_feed = (op_feed - 280.0) / 280.0
            op_pc = tic_pc.update(plant.pc_temp, dt, feedforward=ff_feed * 25.0)
            op_bz = tic_bz.update(plant.sintering_temp, dt, feedforward=ff_feed * 15.0)
            op_ph = pic_ph.update(plant.ph_top_draft, dt)
            op_kh = pic_kh.update(plant.kiln_hood_press, dt)
            
            # Step physics
            plant.step(dt, {
                'feed_rate': op_feed,
                'pc_fuel_op': op_pc,
                'kiln_fuel_op': op_bz,
                'id_fan_damper': op_ph,
                'cooler_vent_speed': op_kh
            })
            
            # Record trajectory
            writer.writerow([
                round(t, 1), round(plant.raw_meal_feed, 2), round(plant.clinker_production, 2),
                round(plant.kiln_speed, 2), round(plant.sintering_temp, 1), round(plant.pc_temp, 1),
                round(plant.free_lime, 3), round(plant.ph_top_draft, 2), round(plant.kiln_hood_press, 3),
                round(plant.kiln_inlet_o2, 2), round(op_pc, 2), round(op_bz, 2)
            ])
            
            # Print every 60s
            if step_idx % int(60.0 / dt) == 0:
                print(f"{t:>6.0f}s | {plant.raw_meal_feed:>6.1f}t | {plant.clinker_production:>6.1f}t | {plant.kiln_speed:>5.2f}r | {plant.sintering_temp:>6.1f}C | {plant.pc_temp:>6.1f}C | {plant.free_lime:>7.2f}% | {plant.kiln_hood_press:>6.2f}mb")
                
    print("-" * 75)
    print(f"Simulation test completed successfully! Data logged to: {csv_file}")
    print(f"Final Clinker Output: {plant.clinker_production:.1f} t/h | Free Lime: {plant.free_lime:.2f}% | Sintering: {plant.sintering_temp:.1f} °C")

if __name__ == "__main__":
    run_dynamic_test()
