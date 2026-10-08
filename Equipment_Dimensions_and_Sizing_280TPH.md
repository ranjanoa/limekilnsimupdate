# EQUIPMENT DIMENSIONS AND SIZING SPECIFICATION
## CEMENT CLINKER MANUFACTURING LINE (FORNO 3 / PRÉ-AQUECEDOR)
**Production Baseline**: Raw Meal Feed Rate = **280.0 t/h** | Clinker Production = **175.0 t/h** ($4,200\text{ metric tons/day}$)  
**Target Application**: Dynamic Process Simulation (Siemens SIMIT CTE / FLOWNET & Real-Time HMI Simulator)  
**Standard**: Cement Pyroprocessing Engineering Design Standard (VDZ / KHD / FLS Benchmark)

---

## 1. DESIGN BASIS & VOLUMETRIC CAPACITIES

For a modern dry-process cement clinker line producing $175.0\text{ t/h}$ ($4,200\text{ tpd}$) of Portland clinker with a $54.1\%$ Precalciner / $45.9\%$ Kiln thermal split and $41.5\%$ alternative fuel substitution:

| Parameter | Value | Engineering Units | Reference Benchmark |
| :--- | :--- | :--- | :--- |
| **Clinker Production Rate** | **175.00** | metric tons / hour | Nominal design rate |
| **Daily Clinker Output** | **4,200** | metric tons / 24 hr | Continuous 100% MCR |
| **Raw Meal Feed Rate** | **280.00** | metric tons / hour (dry) | $1.60\text{ t meal / t clinker}$ |
| **Total Flue Gas Volume (Preheater Top)**| **291,500** | $\text{Nm}^3/\text{h}$ (wet) | $\approx 1.66\text{ Nm}^3/\text{kg clinker}$ |
| **Preheater Top Actual Gas Volume** | **732,000** | $\text{m}^3/\text{h}$ @ $413\text{ }^\circ\text{C}$, $-56\text{ mbar}$ | Volumetric fan intake |
| **Tertiary Air Actual Volume** | **436,000** | $\text{m}^3/\text{h}$ @ $862\text{ }^\circ\text{C}$, $-3.6\text{ mbar}$ | $105,000\text{ Nm}^3/\text{h}$ |
| **Kiln Inlet Gas Actual Volume** | **466,000** | $\text{m}^3/\text{h}$ @ $1050\text{ }^\circ\text{C}$, $-1.3\text{ mbar}$ | $96,220\text{ Nm}^3/\text{h}$ |
| **Cooler Vent Air Actual Volume** | **285,000** | $\text{m}^3/\text{h}$ @ $258\text{ }^\circ\text{C}$, $-4.6\text{ mbar}$ | $147,000\text{ Nm}^3/\text{h}$ |

---

## 2. DETAILED EQUIPMENT GEOMETRICAL DIMENSIONS

### 2.1 Rotary Kiln (Forno 3)
* **Kiln Type**: 3-pier direct-drive rotary kiln with hydraulic thruster.
* **Internal Shell Diameter (Steel)**: $D_{\text{steel}} = 4.80\text{ m}$.
* **Refractory Lining Thickness**:
  - Burning zone ($0 - 18\text{ m}$ from discharge): $220\text{ mm}$ (Basic Magnesite-Spinel bricks).
  - Transition zone ($18 - 42\text{ m}$): $200\text{ mm}$ (High-Alumina / Spinel bricks).
  - Calcining/inlet zone ($42 - 70\text{ m}$): $180\text{ mm}$ (Fireclay / Andalusite bricks).
* **Mean Effective Internal Diameter**: $D_i = 4.40\text{ m}$.
* **Overall Shell Length**: $L = 70.0\text{ m}$ ($L/D_i \approx 15.9$).
* **Kiln Incline / Slope**: $S = 3.50\%$ ($2.0^\circ$).
* **Rotational Speed**: Nominal $3.79\text{ rpm}$ (`L3S01`), range $0.5 - 4.5\text{ rpm}$.
* **Total Internal Volume**:
  $$V_{\text{kiln}} = \frac{\pi}{4} \times D_i^2 \times L = \frac{\pi}{4} \times (4.40)^2 \times 70.0 = \mathbf{1,064.4\text{ m}^3}$$
* **Volumetric Heat Release Rate**:
  $$q_v = \frac{\dot{Q}_{\text{kiln}}}{V_{\text{kiln}}} = \frac{72.46\text{ MW}}{1,064.4\text{ m}^3} = \mathbf{68.08\text{ kW/m}^3} \quad (58.5\text{ Mcal/m}^3\cdot\text{h})$$
* **Volumetric Clinker Production Intensity**:
  $$I_v = \frac{4,200\text{ tpd}}{1,064.4\text{ m}^3} = \mathbf{3.95\text{ tpd/m}^3}$$
* **Total External Surface Area (Radiation/Convection)**:
  $$A_{\text{shell}} = \pi \times D_{\text{steel}} \times L = \pi \times 4.80 \times 70.0 = \mathbf{1,055.6\text{ m}^2}$$
* **Bed Material Holdup**:
  $$V_{\text{bed}} = 10.96\% \times 1,064.4\text{ m}^3 = \mathbf{116.6\text{ m}^3} \quad (\approx 155\text{ tons of material})$$
* **Solid Residence Time (Saeman Equation)**:
  $$\tau_{\text{kiln}} = \frac{1.77 \cdot L \cdot \sqrt{\theta}}{S \cdot D_i \cdot \omega} = \frac{1.77 \times 70.0 \times \sqrt{38^\circ}}{0.035 \times 4.40 \times 3.79} = \mathbf{26.8\text{ minutes}}$$

---

### 2.2 In-Line Precalciner & Mixing Chamber (PC)
* **Vessel Geometry**: Vertical cylindrical reaction vessel with conical lower reduction and upper swan-neck duct connecting to Cyclones 4N/4P.
* **Internal Diameter (Inside Refractory)**: $D_{\text{calc}} = 6.80\text{ m}$ (Steel shell: $7.24\text{ m}$, lining $220\text{ mm}$).
* **Total Height**: $H_{\text{calc}} = 45.0\text{ m}$.
* **Total Active Reaction Volume**:
  $$V_{\text{calc}} = \frac{\pi}{4} \times D_{\text{calc}}^2 \times H_{\text{eff}} \approx \mathbf{1,520\text{ m}^3}$$
* **Specific Calciner Volume**:
  $$v_{\text{sp}} = \frac{1,520\text{ m}^3}{4,200\text{ tpd}} = \mathbf{0.362\text{ m}^3/\text{tpd clinker}}$$
  *(Optimal for alternative fuel burnout: $>0.35\text{ m}^3/\text{tpd})$*
* **Gas Flow in Calciner**:
  - Operating Temperature: $907\text{ }^\circ\text{C}$ ($1,180\text{ K}$).
  - Actual gas volumetric rate:
    $$\dot{V}_{\text{gas,act}} = 205,300\text{ Nm}^3/\text{h} \times \frac{1,180}{273} \times \frac{1}{3,600} = \mathbf{246.5\text{ m}^3/\text{s}}$$
* **Superficial Gas Velocity**:
  $$v_{\text{gas,calc}} = \frac{246.5\text{ m}^3/\text{s}}{\frac{\pi}{4} \times (6.80)^2} = \mathbf{6.79\text{ m/s}}$$
  *(Maintains raw meal fully entrained in pneumatic transport: $v > 5.5\text{ m/s}$)*
* **Gas Residence Time**:
  $$\tau_{\text{gas,calc}} = \frac{V_{\text{calc}}}{\dot{V}_{\text{gas,act}}} = \frac{1,520\text{ m}^3}{246.5\text{ m}^3/\text{s}} = \mathbf{6.17\text{ seconds}}$$
* **Solid Raw Meal Retention Time (with slip factor $s \approx 0.6$)**:
  $$\tau_{\text{solid,calc}} = \frac{\tau_{\text{gas}}}{s} \approx \mathbf{10.3\text{ seconds}}$$
  *(Allows $>92\%$ calcination of $CaCO_3$ and complete combustion of CDR refuse-derived fuels)*.

---

### 2.3 Tertiary Air Duct (Conduta de Ar Terciário)
* **Connecting Path**: Clinker cooler takeoff hood $\rightarrow$ Settling cyclone `K3M480C` $\rightarrow$ Precalciner burner inlet.
* **Tertiary Air Mass Flow**: $135.77\text{ t/h}$ ($105,000\text{ Nm}^3/\text{h}$).
* **Operating Temperature**: $862\text{ }^\circ\text{C}$ ($1,135\text{ K}$), Pressure: $-3.6\text{ mbar}$ (`K3P17`).
* **Actual Volumetric Flow Rate**:
  $$\dot{V}_{\text{act,TAD}} = 105,000 \times \frac{1,135}{273} \times \frac{1}{3,600} = \mathbf{121.25\text{ m}^3/\text{s}}$$
* **Design Velocity Target**: $26.5\text{ m/s}$ (Prevents dust fallout, avoids abrasive refractory wear).
* **Required Cross-Sectional Area**:
  $$A_{\text{TAD}} = \frac{121.25\text{ m}^3/\text{s}}{26.5\text{ m/s}} = \mathbf{4.575\text{ m}^2}$$
* **Internal Diameter (Inside Refractory)**:
  $$D_{i,\text{TAD}} = \sqrt{\frac{4 \times 4.575}{\pi}} = \mathbf{2.41\text{ m}}$$
* **Outer Steel Shell Diameter**: $D_{o,\text{TAD}} = 2.85\text{ m}$ ($220\text{ mm}$ refractory + insulation).
* **Total Centerline Length**: $L_{\text{TAD}} = 64.0\text{ m}$.
* **Dust Settling Cyclone (`K3M480C`)**:
  - Diameter: $4.20\text{ m}$, Height: $9.50\text{ m}$.
  - Dust drain temperature: $290\text{ }^\circ\text{C}$ (returns fallen dust to kiln feed shelf).
  - Regulating Damper: `K3G36` ($99\%$ open).

---

### 2.4 Dual-String 4-Stage Preheater Cyclones (Strings N & P)

All cyclone dimensions are specified on inside refractory diameter ($D_i$). Height ($H$) is total height from top plate to apex cone discharge.

```
                          STAGE 1 CYCLONES (1N & 1P)
                          Di = 5.20 m | H = 12.8 m | Vol = 210 m3
                                      |
                          STAGE 2 CYCLONES (2N & 2P)
                          Di = 5.60 m | H = 13.8 m | Vol = 265 m3
                                      |
                          STAGE 3 CYCLONE / CHAMBER (3)
                          Di = 6.20 m | H = 14.8 m | Vol = 350 m3
                                      |
                          STAGE 4 CYCLONES (4N & 4P)
                          Di = 6.50 m | H = 16.0 m | Vol = 415 m3
```

| Cyclone Unit | Inside Dia ($D_i$) | Total Height ($H$) | Cylinder Ht ($h_c$) | Cone Ht ($h_k$) | Volume ($m^3$) | Dip Tube Dia ($D_e$) | Dust Sep. Eff ($\eta$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cyclone 1N** | $5.20\text{ m}$ | $12.80\text{ m}$ | $5.20\text{ m}$ | $7.60\text{ m}$ | $210\text{ m}^3$ | $2.30\text{ m}$ | $96.8\%$ |
| **Cyclone 1P** | $5.20\text{ m}$ | $12.80\text{ m}$ | $5.20\text{ m}$ | $7.60\text{ m}$ | $210\text{ m}^3$ | $2.30\text{ m}$ | $97.2\%$ |
| **Cyclone 2N** | $5.60\text{ m}$ | $13.80\text{ m}$ | $5.60\text{ m}$ | $8.20\text{ m}$ | $265\text{ m}^3$ | $2.50\text{ m}$ | $89.5\%$ |
| **Cyclone 2P** | $5.60\text{ m}$ | $13.80\text{ m}$ | $5.60\text{ m}$ | $8.20\text{ m}$ | $265\text{ m}^3$ | $2.50\text{ m}$ | $90.2\%$ |
| **Stage 3 Chamber**| $6.20\text{ m}$| $14.80\text{ m}$ | $6.20\text{ m}$ | $8.60\text{ m}$ | $350\text{ m}^3$ | $2.80\text{ m}$ | $88.0\%$ |
| **Cyclone 4N** | $6.50\text{ m}$ | $16.00\text{ m}$ | $6.50\text{ m}$ | $9.50\text{ m}$ | $415\text{ m}^3$ | $2.95\text{ m}$ | $92.0\%$ |
| **Cyclone 4P** | $6.50\text{ m}$ | $16.00\text{ m}$ | $6.50\text{ m}$ | $9.50\text{ m}$ | $415\text{ m}^3$ | $2.95\text{ m}$ | $93.5\%$ |

* **Total Preheater Tower Structural Height**: $118.0\text{ m}$.
* **Connecting Gas Riser Ducts**:
  - Duct 1-2: $D_i = 3.20\text{ m}$, gas velocity $\approx 18.5\text{ m/s}$.
  - Duct 2-3: $D_i = 3.50\text{ m}$, gas velocity $\approx 17.0\text{ m/s}$.
  - Duct 3-4: $D_i = 3.80\text{ m}$, gas velocity $\approx 16.0\text{ m/s}$.
  - Kiln Riser to Calciner: $D_i = 3.40\text{ m}$, gas velocity $\approx 22.0\text{ m/s}$.

---

### 2.5 Clinker Grate Cooler (Arrefecedor de Grelha)
* **Cooler Technology**: Reciprocating stepped grate cooler with mechanical aeration floor and hydraulic lane drives.
* **Clinker Capacity**: $175.0\text{ t/h}$ ($4,200\text{ metric tons/day}$).
* **Specific Grate Area Loading**:
  $$q_{\text{grate}} = \frac{4,200\text{ tpd}}{105.0\text{ m}^2} = \mathbf{40.0\text{ tpd/m}^2}$$
* **Grate Dimensions**:
  - Active Width ($W$): $3.80\text{ m}$.
  - Active Aerated Length ($L_{\text{grate}}$): $27.65\text{ m}$.
  - Total Active Grate Surface: $A_{\text{active}} = 3.80 \times 27.65 = \mathbf{105.07\text{ m}^2}$.
* **Undergrate Aeration Compartments (6 Pressure Chambers)**:
  - **Chamber 1 (Recuperation / Impact zone)**: Area $12.0\text{ m}^2$, $P = +85\text{ mbar}$, High-pressure fan (`L3M330`), feeds Secondary Air.
  - **Chamber 2 (Recuperation)**: Area $15.5\text{ m}^2$, $P = +72\text{ mbar}$, Fan (`L3M335`), feeds Secondary/Tertiary Air.
  - **Chamber 3 (Tertiary Air takeoff)**: Area $18.5\text{ m}^2$, $P = +58\text{ mbar}$, Fan (`L3M207 = 34 A`), feeds Tertiary Air.
  - **Chamber 4 (Cooling)**: Area $20.0\text{ m}^2$, $P = +45\text{ mbar}$, Fan (`L3M433 = 10 A`).
  - **Chamber 5 (Cooling)**: Area $20.0\text{ m}^2$, $P = +35\text{ mbar}$, Fan (`L3M209`).
  - **Chamber 6 (Final cooling)**: Area $19.0\text{ m}^2$, $P = +25\text{ mbar}$, Fan (`L3M202`).
* **Mean Clinker Bed Thickness**: $h_{\text{bed}} = 0.65\text{ m}$ to $0.72\text{ m}$.
* **Clinker Residence Time on Grate**: $\tau_{\text{cooler}} \approx \mathbf{28.5\text{ minutes}}$ at nominal stroke rate.

---

### 2.6 Industrial Fans & Dedusting Filters

| Fan / Equipment Tag | Service Description | Design Gas Flow ($Nm^3/h$) | Operating Gas Flow ($m^3/h$) | Gas Temp ($^\circ C$) | Static Differential Head | Installed Motor Power |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Preheater ID Fan (`K3M487`)**| Preheater draft & process gas| $291,500$ | $685,000$ | $413$ | $-75.0\text{ mbar}$ | $3,150\text{ kW}$ |
| **Cooler Vent Fan (`L3M366`)** | Cooler excess vent air to baghouse| $147,000$ | $265,000$ | $258$ | $-32.0\text{ mbar}$ | $750\text{ kW}$ (Current: $289\text{ A}$, $908\text{ rpm}$)|
| **Cooler Chamber 1 Fan (`L3M330`)**| High-pressure clinker quenching| $38,000$ | $41,500$ | $25$ | $+85.0\text{ mbar}$ | $200\text{ kW}$ |
| **Cooler Chamber 2 Fan (`L3M335`)**| Primary clinker recuperation | $52,000$ | $56,700$ | $25$ | $+72.0\text{ mbar}$ | $250\text{ kW}$ |
| **Cooler Chamber 3 Fan (`L3M207`)**| Tertiary air zone aeration | $65,000$ | $71,000$ | $25$ | $+58.0\text{ mbar}$ | $280\text{ kW}$ (Current: $34\text{ A}$) |
| **Cooler Chamber 4 Fan (`L3M433`)**| Intermediate cooling | $62,000$ | $67,700$ | $25$ | $+45.0\text{ mbar}$ | $220\text{ kW}$ (Current: $10\text{ A}$) |
| **Cooler Chamber 5/6 Fans** | Final discharge cooling | $113,000$ | $123,000$ | $25$ | $+30.0\text{ mbar}$ | $350\text{ kW}$ |
| **Cooler Baghouse Filter** | Dedusting of cooler exhaust | $147,000$ | $245,000$ | $89$ (Inlet: $258$) | $\Delta P = 10.0\text{ mbar}$ (`L3P318`)| Net filtering area: $4,200\text{ m}^2$ |

---

## 3. MASS & THERMAL TIME CONSTANTS (FOR DYNAMIC SIMULATION)

These first-principles dynamic time constants are built into the SIMIT CTE transfer functions and state-space ODE solvers:

```
  SUB-PROCESS TIME CONSTANTS:
  +--------------------------------------------------------------------------+
  | Preheater Gas Flow Draft Dynamics:         tau = 0.8 to 1.5 seconds      |
  | Preheater Suspension Heat Transfer:        tau = 3.0 to 6.0 seconds      |
  | Precalciner Combustion & Decarbonation:    tau = 8.0 to 15.0 seconds     |
  | Kiln Hood Pressure Wave Dynamics:          tau = 0.5 to 1.2 seconds      |
  | Kiln Flame & Gas Temperature Response:     tau = 25.0 to 45.0 seconds    |
  | Cooler Aeration Bed Differential Pressure: tau = 5.0 to 10.0 seconds     |
  | Kiln Sintering Bed Thermal Inertia:        tau = 12.0 to 18.0 minutes    |
  | Kiln Bed Solids Transportation Delay:      tau = 26.8 minutes            |
  | Clinker Cooler Grate Clinker Residence:    tau = 28.5 minutes            |
  | Clinker Free Lime Chemical Stabilization:  tau = 35.0 to 50.0 minutes    |
  +--------------------------------------------------------------------------+
```
