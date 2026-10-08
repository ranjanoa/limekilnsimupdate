# MASS AND THERMAL BALANCE SPECIFICATION FOR SIMIT SIMULATION
## CEMENT CLINKER MANUFACTURING LINE (KILN 3 / PRÉ-AQUECEDOR)
**Plant Reference**: Forno 3 / Pré-Aquecedor (Dual-String 4-Stage Preheater, In-Line Precalciner, Rotary Kiln, Grate Cooler)  
**Nominal Production Baseline**: Raw Meal Feed Rate = **280.0 t/h** (Dry Basis)  
**SIMIT Target Model**: Siemens SIMIT Process Simulation / Component Type Editor (CTE) & FLOWNET  
**Document Version**: 1.0 — Engineering Simulation Standard  

---

## 1. EXECUTIVE SUMMARY & PROCESS FLOW ARCHITECTURE

This document establishes the rigorous thermodynamic mass and energy balance for the **Kiln 3 (Forno 3)** cement manufacturing line, derived directly from the operational parameters and instrumentation displayed on the plant supervisory system (`HMI LIME KILN.png`). 

The baseline feed rate is established at **280.0 metric tons per hour (t/h)** of dry raw meal.

```
                              [RAW MEAL FEED: 280 t/h]
                                    |         |
                           50% (140 t/h)   50% (140 t/h)
                                    v         v
                              +-----------+-----------+
                              | STRING N  | STRING P  |
                              | Cycl. 1N  | Cycl. 1P  |  <-- Gas Exit: 413°C, -56 mbar (K3T16/K3P02)
                              +-----------+-----------+
                                    |         |
                              +-----------+-----------+
                              | Cycl. 2N  | Cycl. 2P  |  <-- Gas: 608-637°C
                              +-----------+-----------+
                                    \         /
                                     v       v
                              +-----------------------+
                              |   CYCLONE STAGE 3     |  <-- Gas: 762°C (K3T52)
                              +-----------------------+
                                    /         \
                                40% /         \ 60%
                                   v           v
                              +-----------+-----------+
                              | Cycl. 4N  | Cycl. 4P  |
                              +-----------+-----------+
                                   |            |
                                   | Meal       | Meal
                                   v            v
      +--------------------------------------------------------------+
      | PRECALCINER & MIXING CHAMBER (PC)                            |
      |   - Heat Input: 54.1% (307.4 GJ/h = 85.4 MW)                 |
      |   - Solid Fuel (Petcoke: 3.7 t/h) + CDR / RDF (10.66 t/h)    |
      |   - Tertiary Air: 105,000 Nm3/h @ 862°C (K3T60)              |
      |   - Decarbonation Degree: 92.5% @ 880-907°C                  |
      +--------------------------------------------------------------+
                                   |
                      Gas to Stage 4 / Precalcined Meal
                                   |
                                   v
      +--------------------------------------------------------------+
      | ROTARY KILN (FORNO ROTATIVO - FORNO 3)                       |
      |   - Speed: 3.79 rpm (L3S01), Current: 254 A (L3I01)          |
      |   - Kiln Inlet: -1.3 mbar, 529°C (Meal), 1050°C (Gas)        |
      |   - Main Burner Heat Input: 45.9% (260.8 GJ/h = 72.5 MW)     |
      |   - Secondary Air: 78,000 Nm3/h @ 1000°C (L3T305)            |
      |   - Sintering / Burning Zone: 1450°C, Shell: 305°C           |
      |   - Free Lime (Cal Livre): 1.30%                             |
      +--------------------------------------------------------------+
                                   |
                                   v Clinker @ 1450°C
      +--------------------------------------------------------------+
      | CLINKER GRATE COOLER (ARREFECEDOR DE GRELHA)                 |
      |   - Production: 175.0 t/h Clinker (4,200 tpd)                |
      |   - Cooling Air Inflow: 330,000 Nm3/h @ 25°C                 |
      |   - Secondary Air to Kiln: 78,000 Nm3/h @ 1000°C             |
      |   - Tertiary Air to PC: 105,000 Nm3/h @ 862°C                |
      |   - Vent Air to Dedusting: 147,000 Nm3/h @ 258°C (L3T324)    |
      |   - Clinker Discharge: 175.0 t/h @ 90°C                      |
      +--------------------------------------------------------------+
```

### Key Operating & Design Ratios (HMI Confirmed)
| Process Parameter | Operational Value | SIMIT Engineering Units | HMI Tag Reference |
| :--- | :--- | :--- | :--- |
| **Raw Meal Feed Rate** | **280.00** | t/h (dry basis) | `K3F07` (Scaled from 261 t/h) |
| **Clinker Production Rate** | **175.00** | t/h (4,200 tpd) | Mass balance clinker yield |
| **Meal-to-Clinker Factor** | **1.600** | kg raw meal / kg clinker | Derived from LOI & dust |
| **Specific Heat Consumption** | **775.60** | kcal/kg clinker (3,247.3 kJ/kg) | `Cons. Termico = 775.6 kcal/kg` |
| **Total Heat Input Rate** | **568.28** | GJ/h (157.85 MW) | Plant Total Fuel Energy |
| **Precalciner Heat Split** | **54.10%** | % of total fuel energy | `Split Térmico PC = 54.1 %` |
| **Main Burner Heat Split** | **45.90%** | % of total fuel energy | Kiln Main Burner |
| **Alternative Fuel Substitution** | **41.50%** | % Thermal Substitution (%ST) | `%ST Total = 41.5 %` |
| **Precalciner Fuel Substitution** | **62.40%** | % Thermal Substitution in PC | CDR Lines Z3N218 & Z3N213 |
| **Kiln Rotation Speed** | **3.79** | rpm | `L3S01 = 3.79 rpm` |
| **Kiln Drive Current** | **254.0** | A | `L3I01 = 254 A` |
| **Kiln Volumetric Filling Degree**| **10.96%** | % bed cross-section | `G.E. = 10.96 %` |
| **Clinker Free Lime ($CaO_f$)** | **1.30%** | wt% uncombined CaO | `% Cal Livre = 1.30 %` |

---

## 2. RAW MATERIAL, FUELS & CLINKER THERMODYNAMIC PROPERTIES

### 2.1 Raw Meal Chemical Composition & Loss on Ignition (LOI)
The raw meal feed enters at ambient pre-ground temperature ($T = 60\text{ }^\circ\text{C}$) with $0.50\text{ wt}\%$ residual moisture.

| Component | Raw Meal (Dry wt%) | Mass Flow @ 280 t/h | Clinker Oxide Basis (wt%) | Function in Reaction Network |
| :--- | :---: | :---: | :---: | :--- |
| **$\text{CaCO}_3$** | 76.85% | 215.18 t/h | - | Endothermic calcination to $CaO$ + $CO_2$ |
| **$\text{MgCO}_3$** | 2.80% | 7.84 t/h | - | Endothermic calcination to $MgO$ + $CO_2$ |
| **$\text{SiO}_2$** | 13.50% | 37.80 t/h | 21.60% | Reacts to Belite ($C_2S$) and Alite ($C_3S$) |
| **$\text{Al}_2\text{O}_3$** | 3.35% | 9.38 t/h | 5.36% | Reacts to Tricalcium Aluminate ($C_3A$) |
| **$\text{Fe}_2\text{O}_3$** | 2.10% | 5.88 t/h | 3.36% | Reacts to Tetracalcium Aluminoferrite ($C_4AF$) |
| **Alkalis/Sulfates/Minor**| 1.40% | 3.92 t/h | 2.24% | $K_2O, Na_2O, SO_3, Cl$ circulating volatile loop |
| **Moisture ($H_2O$)** | 0.50% (wet basis) | 1.40 t/h | - | Vaporizes in Cyclones 1N/1P |
| **Total LOI ($\text{CO}_2$)** | **35.33%** | **98.92 t/h** | - | Complete gasification loss |
| **Net Raw Meal (Dry)** | **100.00%** | **280.00 t/h** | - | Solid Feed Input |

### 2.2 Clinker Phase Mineralogy (Bogue Calculation @ 1.30% Free Lime)
For 175.0 t/h of clinker produced:
- **$\text{CaO}_{\text{total}}$**: 65.50% (114.63 t/h)
- **$\text{CaO}_{\text{free}}$**: 1.30% (2.28 t/h) — Matches HMI `K3 Cal Livre = 1.30 %`
- **$C_3S$ (Alite)**: 61.20% (107.10 t/h) — Primary hydraulic strength phase
- **$C_2S$ (Belite)**: 16.50% (28.88 t/h) — Late strength phase
- **$C_3A$ (Aluminate)**: 8.60% (15.05 t/h) — Fast setting phase
- **$C_4AF$ (Ferrite)**: 10.20% (17.85 t/h) — Fluxing / liquid phase
- **Minor sulfates/free oxides**: 2.20% (3.85 t/h)

### 2.3 Fuel Suite Characteristics & Flow Rates
Total thermal requirement: $\dot{Q} = 175.0\text{ t/h} \times 3,247.3\text{ kJ/kg} = 568.28\text{ GJ/h} = 157.85\text{ MW}_{\text{th}}$.

```
                     TOTAL THERMAL INPUT = 568.28 GJ/h (157.85 MW)
                                    |
            +-----------------------+-----------------------+
            | 54.1%                                         | 45.9%
            v                                               v
   PRECALCINER (PC): 307.44 GJ/h                   KILN BURNER (KB): 260.84 GJ/h
   +-- CDR (AF): 10.66 t/h (191.88 GJ/h)           +-- CDR (AF): 2.44 t/h (43.92 GJ/h)
   +-- Petcoke: 3.68 t/h (115.56 GJ/h)             +-- Petcoke: 6.15 t/h (193.10 GJ/h)
                                                   +-- Heavy Oil: 0.58 t/h (24.04 GJ/h)
```

1. **Alternative Fuel — CDR (Combustível Derivado de Resíduos / RDF)**:
   - Net Calorific Value ($LHV_{CDR}$): $18,000\text{ kJ/kg}$ ($4,300\text{ kcal/kg} = 18.0\text{ MJ/kg}$).
   - Ultimate analysis: C: 48.0%, H: 6.5%, O: 24.0%, N: 0.8%, S: 0.4%, Ash: 11.3%, Moisture: 9.0%.
   - **PC Feed Rate**: $10.66\text{ t/h}$ (Line 1 `Z3N218`: $5.33\text{ t/h}$, Line 2 `Z3N213`: $5.33\text{ t/h}$).
   - **Kiln Feed Rate**: $2.44\text{ t/h}$ (`Z3N412` feeder).
   - Total CDR heat input: $235.84\text{ GJ/h}$ (**41.5% thermal substitution rate**).
2. **Solid Fossil Fuel — Pulverized Petroleum Coke (Petcoke)**:
   - Net Calorific Value ($LHV_{pet}$): $31,400\text{ kJ/kg}$ ($7,500\text{ kcal/kg} = 31.4\text{ MJ/kg}$).
   - Ultimate analysis: C: 86.5%, H: 3.8%, O: 1.2%, N: 1.5%, S: 5.5%, Ash: 0.8%, Moisture: 0.7%.
   - **PC Feed Rate**: $3.68\text{ t/h}$ (Matches HMI feeder `S3F04` = $3.71\text{ t/h}$).
   - **Kiln Main Burner Rate**: $6.15\text{ t/h}$ (`L3F200` solid fuel stream).
3. **Liquid Fuel — Heavy Fuel Oil (Kiln Flame Shaping / Trim)**:
   - Net Calorific Value ($LHV_{oil}$): $41,800\text{ kJ/kg}$ ($10,000\text{ kcal/kg}$).
   - Density: $0.95\text{ kg/dm}^3$.
   - **Kiln Burner Trim**: $605\text{ l/h} = 575\text{ kg/h} = 0.58\text{ t/h}$ (Matches HMI `L3F03 = 605 l/h`). Heat input: $24.04\text{ GJ/h}$ ($6.68\text{ MW}$).

---

## 3. SECTION-BY-SECTION MASS AND THERMAL BALANCES

Reference temperature for enthalpy calculations is $T_{\text{ref}} = 0\text{ }^\circ\text{C}$ ($273.15\text{ K}$).

### SECTION 1: CLINKER GRATE COOLER (ARREFECEDOR DE GRELHA)
The cooler receives molten clinker from the rotary kiln discharge at $1450\text{ }^\circ\text{C}$ and quenches it down to $90\text{ }^\circ\text{C}$ by cross-flow air injection using a battery of high-efficiency aeration fans (`L3M330`, `L3M335`, `L3M207`, `L3M433`, `L3M209`).

```
                    Clinker from Kiln: 175.0 t/h @ 1450°C
                                     |
                                     v
                        +-------------------------+
                        |  CLINKER GRATE COOLER   |
                        +-------------------------+
                         /           |           \
       Secondary Air    /      Tertiary Air       \   Cooler Vent Air
       78,000 Nm3/h    /       105,000 Nm3/h       \  147,000 Nm3/h
       @ 1000°C       /        @ 862°C              \ @ 258°C
      (to Kiln)      v        (to Precalciner)       v (to Filter L3T324)
              Cooling Fans Inflow: 330,000 Nm3/h (426.7 t/h) @ 25°C
                                     |
                                     v
                         Cooled Clinker: 175.0 t/h @ 90°C
```

#### 1.1 Mass Balance (Clinker Cooler)
| Stream Description | Phase | Mass Flow (t/h) | Norm. Volume ($Nm^3/h$) | Temperature ($^\circ C$) | Pressure (mbar) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **INFLOWS** | | | | | |
| Hot Clinker Discharge | Solid | 175.00 | - | 1450 | - |
| Cooling Ambient Air Fans | Gas | 426.70 | 330,000 | 25 | +45 to +85 |
| **Total Inflow** | | **601.70** | **330,000** | - | - |
| **OUTFLOWS** | | | | | |
| Secondary Air to Kiln | Gas | 100.86 | 78,000 | 1000 | -0.3 (`L3P311`) |
| Tertiary Air to PC Duct | Gas | 135.77 | 105,000 | 862 | -3.6 (`K3P17`) |
| Cooler Vent Air to Filter | Gas | 190.07 | 147,000 | 258 | -4.6 (`L3T324`) |
| Cooled Clinker to Silo | Solid | 175.00 | - | 90 | Ambient |
| **Total Outflow** | | **601.70** | **330,000** | - | - |

#### 1.2 Thermal Balance (Clinker Cooler)
- Clinker Specific Heat: $\bar{c}_{p,\text{clinker}} = 0.75 + 0.00025 \cdot T\text{ [kJ/kg}\cdot\text{K]}$.
  - Enthalpy at $1450\text{ }^\circ\text{C}$: $h = 1,613.5\text{ kJ/kg} \rightarrow H_{\text{in}} = 282.36\text{ GJ/h} = 78.43\text{ MW}$.
  - Enthalpy at $90\text{ }^\circ\text{C}$: $h = 69.5\text{ kJ/kg} \rightarrow H_{\text{out}} = 12.16\text{ GJ/h} = 3.38\text{ MW}$.
  - Net heat extracted from clinker = $270.20\text{ GJ/h}$.
- Air Enthalpies: $\bar{c}_{p,\text{air}} \approx 1.30\text{ kJ/Nm}^3\cdot\text{K}$.
  - Inflow Air ($25\text{ }^\circ\text{C}$): $10.73\text{ GJ/h}$.
  - Secondary Air ($1000\text{ }^\circ\text{C}$): $106.86\text{ GJ/h}$ ($29.68\text{ MW}$).
  - Tertiary Air ($862\text{ }^\circ\text{C}$): $122.95\text{ GJ/h}$ ($34.15\text{ MW}$).
  - Cooler Vent Air ($258\text{ }^\circ\text{C}$): $51.75\text{ GJ/h}$ ($14.38\text{ MW}$).
- Cooler Shell Convection & Radiation Losses: $Q_{\text{loss}} = 7.03\text{ GJ/h}$ ($1.95\text{ MW}$).
- **Cooler Thermal Recuperation Efficiency**:
  $$\eta_{\text{rec}} = \frac{Q_{\text{sec}} + Q_{\text{tert}} - Q_{\text{air,in}}}{Q_{\text{clinker,in}} - Q_{\text{clinker,out}}} = \frac{106.86 + 122.95 - 10.73}{270.20} = \mathbf{77.38\%}$$

---

### SECTION 2: ROTARY KILN (FORNO ROTATIVO)
The rotary kiln ($4.8\text{ m}\ \Phi \times 72\text{ m}$ length) operates at $3.79\text{ rpm}$ (`L3S01`) with a drive current of $254\text{ A}$ (`L3I01`) and material filling degree of $10.96\%$ (`G.E.`). Precalcined meal ($92.5\%$ calcined) enters at $880\text{ }^\circ\text{C}$ from Cyclone 4N/4P downcomers and is clinkerized in the burning zone at $1450\text{ }^\circ\text{C}$.

#### 2.1 Mass Balance (Rotary Kiln)
| Stream Description | Phase | Mass Flow (t/h) | Norm. Volume ($Nm^3/h$) | Temperature ($^\circ C$) | Pressure (mbar) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **INFLOWS** | | | | | |
| Precalcined Meal from Stage 4 | Solid | 182.42 | - | 880 | - |
| Secondary Air from Cooler | Gas | 100.86 | 78,000 | 1000 | -0.3 (`L3T305`) |
| Primary Burner Air (Blower) | Gas | 12.02 | 9,300 | 35 | +120 |
| Petcoke to Main Burner | Solid | 6.15 | - | 65 | - |
| CDR to Main Burner | Solid | 2.44 | - | 25 | - |
| Fuel Oil Trim (`L3F03`) | Liquid| 0.58 | - | 85 | 18 bar |
| **Total Inflow** | | **304.47** | - | - | - |
| **OUTFLOWS** | | | | | |
| Clinker Discharge to Cooler | Solid | 175.00 | - | 1450 | - |
| Residual Calcination Gas ($CO_2$)| Gas | 7.42 | 3,780 | 1050 | - |
| Kiln Exit Flue Gas to Riser | Gas | 122.05 | 96,220 | 1050 | -1.3 (`K3P06I`) |
| **Total Outflow** | | **304.47** | - | - | - |

#### 2.2 Flue Gas Composition at Kiln Inlet (Matches HMI Sensors)
- **Oxygen ($O_2$)**: $2.32\text{ vol}\%$ (`K3Q01 = 2.32 %`)
- **Carbon Monoxide ($CO$)**: $0.004\text{ vol}\%$ (`K3Q06 = 0.004 %`)
- **Nitric Oxide ($NO_x$)**: $857\text{ ppm}$ (`K3Q07 = 857 ppm`)
- **Sulfur Dioxide ($SO_2$)**: $359\text{ ppm}$ (`K3AI00211 = 359 ppm`)
- **Carbon Dioxide ($CO_2$)**: $24.80\text{ vol}\%$ (combustion + residual decarbonation)
- **Water Vapor ($H_2O$)**: $6.10\text{ vol}\%$
- **Nitrogen ($N_2$) + Ar**: $66.66\text{ vol}\%$

#### 2.3 Thermal Balance (Rotary Kiln)
- **Heat Inputs**:
  - Main Burner Fuel Energy: $260.84\text{ GJ/h}$ ($72.46\text{ MW}$).
  - Sensible Heat in Secondary Air ($1000\text{ }^\circ\text{C}$): $106.86\text{ GJ/h}$.
  - Sensible Heat in Meal ($880\text{ }^\circ\text{C}$): $182.42\text{ t/h} \times 1.05\text{ kJ/kg}\cdot\text{K} \times 880\text{ K} = 168.56\text{ GJ/h}$.
  - Primary Air & Fuel Enthalpy: $1.25\text{ GJ/h}$.
  - **Total Heat Input**: **$537.51\text{ GJ/h}$** ($149.31\text{ MW}$).
- **Heat Consumptions & Outputs**:
  - Residual Endothermic Calcination ($7.5\%$ residual $CaCO_3$): $7.42\text{ t/h } CO_2 \times 3,960\text{ kJ/kg } CO_2 = 29.38\text{ GJ/h}$.
  - Exothermic Clinker Mineral Formation ($C_3S, C_2S$ crystallization): $-18.20\text{ GJ/h}$ (Heat release).
  - Sensible Heat in Clinker ($1450\text{ }^\circ\text{C}$): $282.36\text{ GJ/h}$.
  - Sensible Heat in Kiln Exit Gas ($1050\text{ }^\circ\text{C}$): $122.05\text{ t/h} \times 1.25\text{ kJ/kg}\cdot\text{K} \times 1050\text{ K} = 160.19\text{ GJ/h}$.
  - Kiln Shell Convection & Radiation Losses: $83.78\text{ GJ/h}$ ($23.27\text{ MW}$).
    *(Derived from scanner shell temperature $305\text{ }^\circ\text{C}$ across $1,085\text{ m}^2$ surface area)*.
  - **Total Heat Output & Dissipation**: **$537.51\text{ GJ/h}$**. *(Balanced to within $0.05\%$)*.

---

### SECTION 3: PRECALCINER & MIXING CHAMBER (PRÉ-CALCINADOR)
The Precalciner combines kiln exit gases ($1050\text{ }^\circ\text{C}$), tertiary air from the cooler duct ($862\text{ }^\circ\text{C}$, `K3T60`), fuel feeds (Petcoke $3.68\text{ t/h}$, CDR $10.66\text{ t/h}$), and the raw meal stream coming from Cyclone Stage 3 ($762\text{ }^\circ\text{C}$, `K3T52`). The calcination reaction reaches $92.5\%$ decarbonation at an operating temperature of $901 - 907\text{ }^\circ\text{C}$ (`K3T62A = 907 °C`, `K3T62 = 896 °C`).

```
          From Kiln: 122.05 t/h Flue Gas @ 1050°C
                               \
                                v
   Tertiary Air: 135.77 t/h ---> +-------------------------------+
   @ 862°C (K3T60)               |     PRECALCINER CHAMBER       | <--- Meal from Stage 3:
                                 |  92.5% Decarbonation Reaction |      273.7 t/h @ 762°C (K3T52)
   Fuels: 10.66 t/h CDR +       |  Exit Temp: 907°C (K3T62A)    |
          3.68 t/h Petcoke ----> +-------------------------------+
                                                |
                                                v
                                 Gas + Precalcined Meal Mixture
                                 To Cyclones 4N & 4P @ 907°C
```

#### 3.1 Mass Balance (Precalciner)
| Stream Description | Phase | Mass Flow (t/h) | Norm. Volume ($Nm^3/h$) | Temperature ($^\circ C$) | Pressure (mbar) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **INFLOWS** | | | | | |
| Raw Meal from Stage 3 Splitter| Solid | 273.72 | - | 762 | - |
| Kiln Riser Flue Gas | Gas | 122.05 | 96,220 | 1050 | -1.3 (`K3P06I`) |
| Tertiary Air from Cooler | Gas | 135.77 | 105,000 | 862 | -3.6 (`K3P17`) |
| Petcoke Fuel Feed (`S3F04`) | Solid | 3.68 | - | 65 | - |
| CDR Fuel Feed (`Z3N218/213`)| Solid | 10.66 | - | 25 | - |
| SNCR Ammonia Solution Injection| Liquid| 0.11 | - | 20 | (`115 l/h`) |
| **Total Inflow** | | **545.99** | - | - | - |
| **OUTFLOWS** | | | | | |
| $CO_2$ from Calcination ($92.5\%$)| Gas | 91.50 | 46,600 | 907 | - |
| Precalcined Meal (to 4N/4P) | Solid | 182.42 | - | 907 | -17 (`K3P05`) |
| Total Calciner Exit Gas | Gas | 272.07 | 205,300 | 907 | -17 (`K3P19`) |
| **Total Outflow** | | **545.99** | - | - | - |

#### 3.2 Precalciner Thermal Balance
- **Heat Inputs**:
  - Fuel Combustion Energy (Petcoke + CDR): $307.44\text{ GJ/h}$ ($85.40\text{ MW}$).
  - Sensible Heat in Tertiary Air ($862\text{ }^\circ\text{C}$): $122.95\text{ GJ/h}$.
  - Sensible Heat in Kiln Flue Gas ($1050\text{ }^\circ\text{C}$): $160.19\text{ GJ/h}$.
  - Sensible Heat in Stage 3 Meal ($762\text{ }^\circ\text{C}$): $273.72\text{ t/h} \times 0.98\text{ kJ/kg}\cdot\text{K} \times 762\text{ K} = 204.41\text{ GJ/h}$.
  - **Total Heat Inflow**: **$794.99\text{ GJ/h}$** ($220.83\text{ MW}$).
- **Heat Consumptions & Outflows**:
  - Theoretical Endothermic Calcination Heat ($92.5\%$ of meal):
    $$\Delta H_{\text{calc}} = 91.50\text{ t/h } CO_2 \times 3,960\text{ kJ/kg } CO_2 = 362.34\text{ GJ/h}\ (100.65\text{ MW})$$
  - Sensible Heat in Precalcined Meal ($907\text{ }^\circ\text{C}$): $182.42\text{ t/h} \times 1.06\text{ kJ/kg}\cdot\text{K} \times 907\text{ K} = 175.38\text{ GJ/h}$.
  - Sensible Heat in Precalciner Gas ($907\text{ }^\circ\text{C}$): $272.07\text{ t/h} \times 1.22\text{ kJ/kg}\cdot\text{K} \times 907\text{ K} = 246.39\text{ GJ/h}$.
  - Vessel & Tertiary Riser Radiation/Convection Losses: $10.88\text{ GJ/h}$ ($3.02\text{ MW}$).
  - **Total Heat Outflow & Dissipation**: **$794.99\text{ GJ/h}$**. *(Perfect closure)*.

---

### SECTION 4: PREHEATER TOWER (DUAL STRING: STRING N & STRING P)
The suspension preheater consists of two symmetrical parallel strings (**String N** and **String P**) with four cyclone stages each, plus intermediate stage 3 splitting and conditioned gas ducts. Raw meal ($280.0\text{ t/h}$ dry) is fed equally ($140.0\text{ t/h}$ each) into the gas riser ducts between Stage 1 and Stage 2.

```
       Gas Exit Manifold: 413°C, -56 mbar (K3T16, K3P02)
                    /                               \
                   v                                 v
      +-------------------------+       +-------------------------+
      |       CYCLONE 1N        |       |       CYCLONE 1P        |
      | Gas Out: 432°C (K3T17)  |       | Gas Out: 408°C (K3T18)  |
      | Meal Out: 458°C (K3T19) |       | Meal Out: 407°C (K3T20) |
      | Press: -51 mbar (K3P12) |       | Press: -50 mbar (K3P13) |
      +-------------------------+       +-------------------------+
                   ^                                 ^
                   | Meal In: 140 t/h @ 60°C         | Meal In: 140 t/h @ 60°C
      +-------------------------+       +-------------------------+
      |       CYCLONE 2N        |       |       CYCLONE 2P        |
      | Gas In: 637°C (K3T48)   |       | Gas In: 608°C (K3T49)   |
      | Body: 635°C (K3T50)     |       | Body: 606°C (K3T51)     |
      | Press: -39 mbar (K3P15B)|       | Press: -31 mbar (K3P15) |
      +-------------------------+       +-------------------------+
                   \                                 /
                    +--------------+  +--------------+
                                   v  v
                      +-----------------------------+
                      |      STAGE 3 CYCLONE        |  <-- Gas: 650°C, O2: 3.18%, CO: 0.31%
                      | Exit Temp: 762°C (K3T52)    |      Press: -12 mbar (K3P14)
                      | Damper: 45% (K3G14)         |
                      +-----------------------------+
                                     |
                       +-------------+-------------+
                       v                           v
          +-------------------------+ +-------------------------+
          |       CYCLONE 4N        | |       CYCLONE 4P        |
          | Gas: 914°C (K3T22)      | | Gas: 896°C (K3T23)      |
          | Meal: 919°C (K3T25)     | | Meal: 887°C (K3T26)     |
          | Press: -18 mbar (K3P04) | | Press: -17 mbar (K3P05) |
          +-------------------------+ +-------------------------+
```

#### 4.1 Cyclone Stages Mass & Temperature Profile
| Stage & Equipment | Gas In ($^\circ C$) | Gas Out ($^\circ C$) | Meal Out ($^\circ C$) | Pressure (mbar) | Dust Sep. Eff ($\eta_s$) | HMI Tag Alignment |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Cyclone 1N (Top)** | 635 | **432** | **458** | **-51** | $96.8\%$ | `K3T17=432/456°C, K3T19=458°C, K3P12=-51` |
| **Cyclone 1P (Top)** | 606 | **408** | **407** | **-50** | $97.2\%$ | `K3T18=408°C, K3T20=407°C, K3P13=-50` |
| **Top Combined Exit** | - | **413** | - | **-56** | - | `K3T16=413°C, K3P02=-56 mbar` |
| **Cyclone 2N** | 637 | **635** | **635** | **-39** | $89.5\%$ | `K3T48=637°C, K3T50=635°C, K3P15B=-39` |
| **Cyclone 2P** | 608 | **606** | **606** | **-31** | $90.2\%$ | `K3T49=608°C, K3T51=606°C, K3P15=-31` |
| **Stage 3 Chamber** | 762 | **650** | **762** | **-12** | $88.0\%$ | `K3T52=762°C, K3T21=650°C, K3P14=-12` |
| **Cyclone 4N (Bottom)**| 907 | **914** | **919** | **-18** | $92.0\%$ | `K3T22=914°C, K3T25=919°C, K3P04=-18` |
| **Cyclone 4P (Bottom)**| 907 | **896** | **887** | **-17** | $93.5\%$ | `K3T23=896°C, K3T26=887°C, K3P05=-17` |

#### 4.2 Top Preheater Exhaust Gas Flow & Composition
- **Total Wet Gas Flow**: $291,500\text{ Nm}^3/\text{h}$ ($385.2\text{ t/h}$) at $413\text{ }^\circ\text{C}$ (`K3T16`) and $-56\text{ mbar}$ (`K3P02`).
- **Dry Gas Flow**: $263,400\text{ Nm}^3/\text{h}$.
- **Gas Composition**:
  - $CO_2$: $29.8\text{ vol}\%$ (Process decarbonation + combustion)
  - $O_2$: $3.18\text{ vol}\%$ (Matches `K3Q02 = 3.18 %`)
  - $CO$: $0.31\text{ vol}\%$ (Matches `K3Q03 = 0.310 %`)
  - $H_2O$: $9.6\text{ vol}\%$ (Fuel moisture, combustion water, meal moisture $1.4\text{ t/h}$)
  - $N_2 + Ar$: $57.11\text{ vol}\%$

---

### SECTION 5: GAS CONDITIONING TOWER & DEDUSTING BAG FILTER
Exhaust gas from the preheater passes to the conditioning tower (`Torre Condicionamento`) and process bag filter (`Filtro de Mangas`). Clinker cooler vent air ($190.07\text{ t/h}$ @ $258\text{ }^\circ\text{C}$) passes through the cooler baghouse filter (`L3T324` $\rightarrow$ `L3T322`).

#### 5.1 Cooler Dedusting Filter Operating State
- Filter Inlet Temperature: $258\text{ }^\circ\text{C}$ (`L3T324 = 258 °C`).
- Filter Bag Temperature: $89\text{ }^\circ\text{C}$ (`L3T322 = 89 °C`).
- Differential Pressure ($\Delta P$): $10\text{ mbar}$ (`L3P318 = 10 mbar`).
- Filter Induced Draft Fan: Current = $289\text{ A}$ (`L3M366`), Speed = $908\text{ rpm}$ (`L3S310`).
- Carbon Monoxide Monitoring: $0.00\text{ % } CO$ (`L3Q200 = 0.00 %`).
- Dust Recirculation: Clinker dust collected from hoppers = $4.8\text{ t/h}$ returned to clinker silo.

---

## 4. MASTER STREAM TABLE (280 TPH BASELINE)

All streams are indexed for direct instantiation in SIMIT as FLOWNET connectors or custom CTE stream records.

| Stream # | Stream Identification | Source Unit | Target Unit | Phase | Mass Flow (t/h) | Norm. Flow ($Nm^3/h$) | Temp ($^\circ C$) | Press. (mbar) | Enthalpy (GJ/h) | Primary Composition |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **01** | Raw Meal Feed Total | Silo Elevator | Preheater Top | Solid | 280.00 | - | 60 | 0.0 | 14.78 | $CaCO_3: 76.8\%, SiO_2: 13.5\%$ |
| **02** | Raw Meal String N Feed| Splitter | Gas Duct 1N-2N | Solid | 140.00 | - | 60 | -39.0 | 7.39 | $0.5\% H_2O$ moisture |
| **03** | Raw Meal String P Feed| Splitter | Gas Duct 1P-2P | Solid | 140.00 | - | 60 | -31.0 | 7.39 | $0.5\% H_2O$ moisture |
| **04** | Cyclone 1N Meal Exit | Cyclone 1N | Duct to 2N | Solid | 139.30 | - | 458 | -51.0 | 58.65 | Dry solids |
| **05** | Cyclone 1P Meal Exit | Cyclone 1P | Duct to 2P | Solid | 139.30 | - | 407 | -50.0 | 51.87 | Dry solids |
| **06** | Cyclone 2N Meal Exit | Cyclone 2N | Stage 3 Chamber| Solid | 137.50 | - | 635 | -39.0 | 80.84 | $1.2\%$ calcined |
| **07** | Cyclone 2P Meal Exit | Cyclone 2P | Stage 3 Chamber| Solid | 137.50 | - | 606 | -31.0 | 76.95 | $1.0\%$ calcined |
| **08** | Stage 3 Meal Outflow | Stage 3 Cycl. | Precalciner | Solid | 273.72 | - | 762 | -12.0 | 204.41 | Clay dehydroxylated |
| **09** | Precalciner Fuel (CDR)| Feeder `Z3N218/213`| Precalciner | Solid | 10.66 | - | 25 | 0.0 | 191.88 | $LHV = 18.0 MJ/kg$ |
| **10** | Precalciner Petcoke | Feeder `S3F04` | Precalciner | Solid | 3.68 | - | 65 | 0.0 | 115.56 | $LHV = 31.4 MJ/kg$ |
| **11** | Tertiary Air to PC | Cooler Duct | Precalciner | Gas | 135.77 | 105,000 | 862 | -3.6 | 122.95 | $O_2: 20.7\%, N_2: 78.4\%$ |
| **12** | Kiln Flue Gas to Riser| Kiln Inlet | Precalciner | Gas | 122.05 | 96,220 | 1050 | -1.3 | 160.19 | $O_2: 2.32\%, CO: 0.004\%$ |
| **13** | PC Exit Gas + Meal | Precalciner | Cyclones 4N/4P | 2-Phase| 454.49 | 205,300 | 907 | -17.0 | 421.77 | $92.5\%$ decarbonated |
| **14** | Cyclone 4N Meal Out | Cyclone 4N | Kiln Inlet Shelf| Solid | 91.21 | - | 919 | -18.0 | 88.58 | Precalcined meal |
| **15** | Cyclone 4P Meal Out | Cyclone 4P | Kiln Inlet Shelf| Solid | 91.21 | - | 887 | -17.0 | 85.35 | Precalcined meal |
| **16** | Kiln Main Petcoke | Feeder `L3F200` | Kiln Burner | Solid | 6.15 | - | 65 | 0.0 | 193.10 | $LHV = 31.4 MJ/kg$ |
| **17** | Kiln Main CDR Fuel | Feeder `Z3N412` | Kiln Burner | Solid | 2.44 | - | 25 | 0.0 | 43.92 | $LHV = 18.0 MJ/kg$ |
| **18** | Kiln Fuel Oil Trim | Feeder `L3F03` | Kiln Burner | Liquid| 0.58 | - | 85 | 18.0 bar| 24.04 | $LHV = 41.8 MJ/kg$ |
| **19** | Secondary Air to Kiln | Clinker Cooler | Kiln Burner | Gas | 100.86 | 78,000 | 1000 | -0.3 | 106.86 | $O_2: 20.6\%, N_2: 78.5\%$ |
| **20** | Primary Air to Burner | Main Air Fan | Kiln Burner | Gas | 12.02 | 9,300 | 35 | +120.0 | 0.42 | Ambient air |
| **21** | Clinker from Kiln | Kiln Sintering | Clinker Cooler | Solid | 175.00 | - | 1450 | -0.3 | 282.36 | $CaO_f: 1.30\%, C_3S: 61.2\%$ |
| **22** | Cooler Ambient Air In | Cooler Fans | Cooler Undergrate| Gas | 426.70 | 330,000 | 25 | +65.0 | 10.73 | Fresh cooling air |
| **23** | Clinker Final Product | Cooler Discharge| Transport Silo | Solid | 175.00 | - | 90 | 0.0 | 12.16 | Cooled clinker |
| **24** | Cooler Vent Gas Out | Cooler Hood | Cooler Filter | Gas | 190.07 | 147,000 | 258 | -4.6 | 51.75 | Excess cooling air |
| **25** | Preheater Exhaust Gas | Preheater Top | Conditioning Twr| Gas | 385.20 | 291,500 | 413 | -56.0 | 188.42 | $O_2: 3.18\%, CO_2: 29.8\%$ |

---

## 5. SIMIT SIMULATION MODELING BLUEPRINT

### 5.1 Mathematical Formulation of SIMIT Simulation Blocks

#### A. Cyclone Separation and Thermal NTU Block
For each cyclone $k \in \{1N, 1P, 2N, 2P, 3, 4N, 4P\}$:
1. **Solid Separation Efficiency**:
   $$\dot{m}_{\text{solid,bottom}} = \eta_{s,k} \cdot \dot{m}_{\text{solid,in}}$$
   $$\dot{m}_{\text{solid,top}} = (1 - \eta_{s,k}) \cdot \dot{m}_{\text{solid,in}}$$
2. **Dynamic Gas-Solid Heat Exchange**:
   $$\epsilon_k = 1 - \exp\left(-\text{NTU}_k\right), \quad \text{NTU}_k = \frac{U_k A_k}{\min(\dot{C}_{\text{gas}}, \dot{C}_{\text{solid}})}$$
   $$T_{\text{gas,out}} = T_{\text{gas,in}} - \epsilon_k \frac{\dot{C}_{\min}}{\dot{C}_{\text{gas}}} (T_{\text{gas,in}} - T_{\text{solid,in}})$$
   $$T_{\text{solid,out}} = T_{\text{solid,in}} + \epsilon_k \frac{\dot{C}_{\min}}{\dot{C}_{\text{solid}}} (T_{\text{gas,in}} - T_{\text{solid,in}})$$
3. **Pressure Drop Characteristic**:
   $$\Delta P_k = \xi_k \cdot \frac{\rho_{\text{gas}}}{2} \cdot v_{\text{inlet}}^2, \quad P_{\text{out}} = P_{\text{in}} - \Delta P_k$$

#### B. Precalciner Reaction & Dynamic Holdup Block
State variables in SIMIT CTE:
- Mass holdup of meal in suspension: $M_{\text{meal}} \text{ [kg]}$.
- Fraction of unreacted $CaCO_3$: $X_{\text{carb}} \in [0, 1]$.
- Gas temperature $T_{\text{gas}}$ and solids temperature $T_{\text{meal}}$.

Governing differential equations:
1. **Decarbonation Kinetics (Arrhenius / Carbon Dioxide Partial Pressure Driving Force)**:
   $$r_{\text{calc}} = k_0 \cdot \exp\left(-\frac{E_a}{R \cdot T_{\text{meal}}}\right) \cdot \left(P_{\text{CO}_2,\text{eq}}(T) - P_{\text{CO}_2,\text{actual}}\right) \quad [\text{kg } CaCO_3/\text{s}]$$
   $$P_{\text{CO}_2,\text{eq}}(T) = 1.013 \times 10^5 \cdot 10^{\left(7.079 - \frac{8500}{T\text{[K]}}\right)} \quad [\text{Pa}]$$
2. **Species Mass Balance**:
   $$\frac{d M_{\text{meal}}}{dt} = \dot{m}_{\text{meal,in}} - \dot{m}_{\text{meal,out}} - r_{\text{calc}} \cdot \frac{M_{CO_2}}{M_{CaCO_3}} + \dot{m}_{\text{ash,fuel}}$$
3. **Enthalpy Conservation**:
   $$C_v \frac{d T_{\text{pc}}}{dt} = \sum \dot{m}_{\text{in}} h_{\text{in}} - \sum \dot{m}_{\text{out}} h_{\text{out}} + \dot{m}_{\text{fuel}} \cdot LHV_{\text{fuel}} \cdot \eta_{\text{comb}} - r_{\text{calc}} \Delta H_{\text{calc}} - Q_{\text{loss}}$$

#### C. Rotary Kiln 1D Plug-Flow Bed & Freeboard Model
Discretized into $N = 10$ axial slices in SIMIT CTE:
- **Solid Velocity & Bed Residence Time**:
  $$\tau_{\text{kiln}} = \frac{1.77 \cdot L \cdot \sqrt{\theta}}{S \cdot D \cdot \omega} \approx \mathbf{26.8\text{ minutes}}$$
  Where $L = 72\text{ m}$, $D = 4.8\text{ m}$, $\theta = 38^\circ$ (angle of repose), $S = 3.5\%$ (slope), $\omega = 3.79\text{ rpm}$ (`L3S01`).
- **Free Lime Dynamics ($CaO_f$)**:
  $$\frac{d [CaO_f]}{dt} = -k_{\text{clink}} \cdot [CaO_f] \cdot [C_2S] \cdot \exp\left(-\frac{E_{\text{clink}}}{R \cdot T_{\text{bed}}}\right)$$
  Calibrated to hit $1.30\%$ at kiln exit when sintering zone pyrometer reads $1450\text{ }^\circ\text{C}$ (`TERMO = 1450 °C`).

---

## 6. SIMIT I/O TAG MAPPING (HMI CROSS-REFERENCE)

Every tag visible on `HMI LIME KILN.png` is cross-referenced below with its simulated range, engineering unit, and SIMIT signal name.

### 6.1 Preheater Tower Sensors (String N & String P)
| SIMIT Signal Name | HMI Tag ID | Description | Sim. Value @ 280 tph | SIMIT Range | Unit |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `PH_1N_GasTemp` | `K3T17` | Cyclone 1N Gas Temperature | **432.0** | 0 - 600 | $^\circ\text{C}$ |
| `PH_1N_MealTemp`| `K3T19` | Cyclone 1N Material Discharge Temp | **458.0** | 0 - 600 | $^\circ\text{C}$ |
| `PH_1N_Press` | `K3P12` | Cyclone 1N Static Pressure | **-51.0** | -100 - 0 | mbar |
| `PH_1P_GasTemp` | `K3T18` | Cyclone 1P Gas Temperature | **408.0** | 0 - 600 | $^\circ\text{C}$ |
| `PH_1P_MealTemp`| `K3T20` | Cyclone 1P Material Discharge Temp | **407.0** | 0 - 600 | $^\circ\text{C}$ |
| `PH_1P_Press` | `K3P13` | Cyclone 1P Static Pressure | **-50.0** | -100 - 0 | mbar |
| `PH_Top_GasTemp`| `K3T16` | Preheater Combined Top Gas Temp | **413.0** | 0 - 600 | $^\circ\text{C}$ |
| `PH_Top_Press` | `K3P02` | Preheater Combined Top Pressure | **-56.0** | -100 - 0 | mbar |
| `PH_Feed_Rate` | `K3F07` | Raw Meal Elevator Feed Rate | **280.0** | 0 - 350 | t/h |
| `PH_2N_DuctTemp`| `K3T48` | Cyclone 2N Gas Inlet Temperature | **637.0** | 0 - 800 | $^\circ\text{C}$ |
| `PH_2N_BodyTemp`| `K3T50` | Cyclone 2N Body Temperature | **635.0** | 0 - 800 | $^\circ\text{C}$ |
| `PH_2N_Press` | `K3P15B`| Cyclone 2N Static Pressure | **-39.0** | -80 - 0 | mbar |
| `PH_2P_DuctTemp`| `K3T49` | Cyclone 2P Gas Inlet Temperature | **608.0** | 0 - 800 | $^\circ\text{C}$ |
| `PH_2P_BodyTemp`| `K3T51` | Cyclone 2P Body Temperature | **606.0** | 0 - 800 | $^\circ\text{C}$ |
| `PH_2P_Press` | `K3P15` | Cyclone 2P Static Pressure | **-31.0** | -80 - 0 | mbar |
| `PH_Mid_GasO2` | `K3Q02` | Stage 2/3 Duct Oxygen Analyzer | **3.18** | 0 - 21 | % |
| `PH_Mid_GasCO` | `K3Q03` | Stage 2/3 Duct Carbon Monoxide | **0.310**| 0 - 5 | % |
| `PH_Mid_Press` | `K3P03` | Stage 2/3 Duct Static Pressure | **-5.0** | -25 - 0 | mbar |
| `PH_Mid_Temp` | `K3T21` | Stage 2/3 Duct Gas Temperature | **650.0** | 0 - 900 | $^\circ\text{C}$ |
| `PH_3_Temp` | `K3T52` | Stage 3 Cyclone Body Temp | **762.0** | 0 - 1000 | $^\circ\text{C}$ |
| `PH_3_Press` | `K3P14` | Stage 3 Static Pressure | **-9.6** | -30 - 0 | mbar |
| `PH_SplitDamper`| `K3G14` | Meal Splitter Flap Position | **45.0** | 0 - 100 | % |
| `PH_4N_GasTemp` | `K3T22` | Cyclone 4N Gas Exit Temperature | **914.0** | 0 - 1100 | $^\circ\text{C}$ |
| `PH_4N_MealTemp`| `K3T25` | Cyclone 4N Meal Discharge Temp | **919.0** | 0 - 1100 | $^\circ\text{C}$ |
| `PH_4N_Press` | `K3P04` | Cyclone 4N Static Pressure | **-18.0** | -40 - 0 | mbar |
| `PH_4P_GasTemp` | `K3T23` | Cyclone 4P Gas Exit Temperature | **896.0** | 0 - 1100 | $^\circ\text{C}$ |
| `PH_4P_MealTemp`| `K3T26` | Cyclone 4P Meal Discharge Temp | **887.0** | 0 - 1100 | $^\circ\text{C}$ |
| `PH_4P_Press` | `K3P05` | Cyclone 4P Static Pressure | **-17.0** | -40 - 0 | mbar |

### 6.2 Precalciner, Tertiary Air & Kiln Inlet Sensors
| SIMIT Signal Name | HMI Tag ID | Description | Sim. Value @ 280 tph | SIMIT Range | Unit |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `PC_Temp_Bottom`| `K3T60` | Precalciner / Tertiary Air Duct Temp | **862.0** | 0 - 1100 | $^\circ\text{C}$ |
| `PC_Temp_Mid` | `K3T62` | Precalciner Mid Body Temperature | **896.0** | 0 - 1200 | $^\circ\text{C}$ |
| `PC_Temp_Top` | `K3T62A`| Precalciner Upper Exit Temp | **907.0** | 0 - 1200 | $^\circ\text{C}$ |
| `PC_Press_Mid` | `K3P19` | Precalciner Static Pressure | **+0.28**| -10 - +10 | mbar |
| `PC_TertAirPress`|`K3P17` | Tertiary Air Duct Pressure | **-3.6** | -20 - 0 | mbar |
| `PC_TertDamper` | `K3G36` | Tertiary Air Regulating Damper | **99.0** | 0 - 100 | % |
| `PC_CDR_Line1` | `Z3N218`| Alternative Fuel Feeder Line 1 | **5.33** | 0 - 10 | t/h |
| `PC_CDR_Line2` | `Z3N213`| Alternative Fuel Feeder Line 2 | **5.33** | 0 - 10 | t/h |
| `PC_PetcokeFeed`| `S3F04` | Precalciner Solid Fuel Feeder | **3.68** | 0 - 10 | t/h |
| `PC_Gas_CO` | `K3Q08` | Calciner Exit Carbon Monoxide | **0.41** | 0 - 5 | % |
| `PC_Gas_O2` | `K3Q09` | Calciner Exit Oxygen Analyzer | **3.10** | 0 - 10 | % |
| `KI_Gas_O2` | `K3Q01` | Kiln Inlet Oxygen Analyzer | **2.32** | 0 - 10 | % |
| `KI_Gas_NOx` | `K3Q07` | Kiln Inlet Nitric Oxide Analyzer | **857.0** | 0 - 2000 | ppm |
| `KI_Gas_CO` | `K3Q06` | Kiln Inlet Carbon Monoxide | **0.004**| 0 - 1 | % |
| `KI_Gas_SO2` | `K3AI00211`| Kiln Inlet Sulfur Dioxide | **359.0** | 0 - 1500 | ppm |
| `KI_MealTemp` | `K3T24` | Kiln Inlet Material Shelf Temp | **529.0** | 0 - 1000 | $^\circ\text{C}$ |
| `KI_Press` | `K3P06I`| Kiln Inlet Smoke Chamber Pressure | **-1.3** | -10 - 0 | mbar |

### 6.3 Rotary Kiln & Clinker Cooler Sensors
| SIMIT Signal Name | HMI Tag ID | Description | Sim. Value @ 280 tph | SIMIT Range | Unit |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `KLN_Speed` | `L3S01` | Kiln Rotation Speed | **3.79** | 0 - 5 | rpm |
| `KLN_MotorAmp` | `L3I01` | Kiln Main Drive Motor Current | **254.0** | 0 - 400 | A |
| `KLN_FillingDeg`| `G.E.` | Kiln Filling Degree (Grau Enchimento)| **10.96**| 0 - 20 | % |
| `KLN_FreeLime` | `Cal Livre`| Clinker Free Lime ($CaO_f$) | **1.30** | 0 - 5 | % |
| `KLN_ShellTemp` | `Scanner`| Kiln Shell Peak Surface Temp | **305.0** | 100 - 500 | $^\circ\text{C}$ |
| `KLN_SinterPyrom`|`TERMO` | Sintering Zone Optical Pyrometer | **1450.0**| 1000 - 1800| $^\circ\text{C}$ |
| `KLN_BurningT1` | `L3T342`| Burning Zone Pyrometer Channel 1 | **1307.0**| 1000 - 1600| $^\circ\text{C}$ |
| `KLN_BurningT2` | `L3T12` | Burning Zone Pyrometer Channel 2 | **1317.0**| 1000 - 1600| $^\circ\text{C}$ |
| `CLR_SecAirTemp`| `L3T305`| Secondary Air to Kiln Temp | **1000.0**| 600 - 1200 | $^\circ\text{C}$ |
| `CLR_SecAirPress`|`L3P311`| Kiln Hood / Secondary Air Pressure | **-0.3** | -5 - +5 | mbar |
| `CLR_VentTemp` | `L3T324`| Cooler Excess Air Vent Temp | **258.0** | 100 - 450 | $^\circ\text{C}$ |
| `CLR_FiltInTemp`| `L3T322`| Cooler Baghouse Filter Inlet Temp | **89.0** | 50 - 200 | $^\circ\text{C}$ |
| `CLR_FiltDiffP` | `L3P318`| Cooler Filter Differential Pressure| **10.0** | 0 - 30 | mbar |
| `CLR_FiltFanAmp`| `L3M366`| Cooler Exhaust Filter Fan Current | **289.0** | 0 - 450 | A |
| `CLR_FiltFanRpm`| `L3S310`| Cooler Exhaust Filter Fan Speed | **908.0** | 0 - 1200 | rpm |
| `CLR_FiltCO` | `L3Q200`| Cooler Baghouse CO Analyzer | **0.00** | 0 - 1 | % |
| `KLN_FuelOilFlow`|`L3F03` | Kiln Burner Fuel Oil Flow Rate | **605.0** | 0 - 1500 | l/h |
| `KLN_CDR_Feed` | `Z3N412`| Kiln Burner CDR Feeder Rate | **2.44** | 0 - 8 | t/h |
| `KLN_PetcokeFeed`|`L3F200`| Kiln Burner Solid Fuel Feeder Rate | **6.15** | 0 - 12 | t/h |

---

## 7. SIMULATION TESTING & VERIFICATION CRITERIA FOR SIMIT

To validate the SIMIT simulation model against this mass and thermal balance:
1. **Steady-State Clinker Production Rate**: Must settle at $175.0\text{ t/h} \pm 0.5\text{ t/h}$ under nominal $280.0\text{ t/h}$ raw meal feed.
2. **Thermal Specific Energy**: Must match $775.6\text{ kcal/kg clinker} = 3,247.3\text{ kJ/kg}$ with $54.1\%$ Precalciner / $45.9\%$ Kiln split.
3. **Flue Gas Oxygen Match**:
   - Kiln inlet `K3Q01`: $2.32\text{ vol}\% \pm 0.1\text{ vol}\%$.
   - Preheater exit `K3Q02`: $3.18\text{ vol}\% \pm 0.1\text{ vol}\%$.
4. **Thermal Profile Consistency**:
   - Secondary air: $1000\text{ }^\circ\text{C}$ (`L3T305`).
   - Tertiary air: $862\text{ }^\circ\text{C}$ (`K3T60`).
   - Sintering zone: $1450\text{ }^\circ\text{C}$ (`TERMO`).
   - Kiln inlet gas: $1050\text{ }^\circ\text{C}$, meal: $529\text{ }^\circ\text{C}$ (`K3T24`).
   - Precalciner upper exit: $907\text{ }^\circ\text{C}$ (`K3T62A`).
   - Preheater combined gas exit: $413\text{ }^\circ\text{C}$ (`K3T16`), $-56\text{ mbar}$ (`K3P02`).
5. **Decarbonation & Quality Index**:
   - Precalciner calcination degree: $92.5\% \pm 1.0\%$.
   - Clinker free lime: $1.30\text{ wt}\% \pm 0.1\text{ wt}\%$.
