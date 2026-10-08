# Kiln 3 Dynamic Simulator & Optimization Testbed

Dynamic First-Principles Pyroprocess Digital Twin, OPC UA Server/Client Bridge, and Interactive Web HMI for cement & lime rotary kiln optimization testing.

---

## 🚀 Features

- **First-Principles Dynamic Physics Engine**: Discretized rotary kiln model (10 axial cells), precalciner decarbonation kinetics, preheater cyclone multi-stage heat exchange, and clinker cooler mass & heat balance.
- **Configurable Online Tag & OPC UA Connection Studio**:
  - Independent per-tag control source selection: assign any individual setpoint or measurement to either **`💻 Local`** (manual operator control via Web HMI faceplates / local tables) or **`⚡ OPC UA`** (external industrial controller / optimizer / DCS bridge).
  - Dynamic runtime tag creation, modification, and deletion with live Node ID mapping, read/write direction, and engineering units.
  - Dedicated Tag Studio modal in the Web HMI (`📡 Tag & OPC Studio`) featuring real-time telemetry updates, category filters, quick bulk toggles, and live connection ping testing.
- **Interactive Web HMI (`simulator/`)**: Real-time synoptic overview mimic, multi-pen strip trend chart, burner/calciner/fan control panels, disturbance injection, and live KPI monitoring.
- **Dual Operating Modes**:
  - **Standalone Mode**: Autonomous client-side integration and simulation directly in any modern browser.
  - **OPC UA Mode**: Industrial OPC UA Server (`opc.tcp://0.0.0.0:4841/freeopcua/server/`) / Client Bridge for integrating external Advanced Process Control (APC), Model Predictive Control (MPC), and Reinforcement Learning (RL) agents.
- **REST & Configuration API**: Live configuration reloading, dynamic tag dictionary endpoints (`/api/tags`, `/api/tags/toggle`, `/api/tags/value`, `/api/tags/create`, `/api/tags/delete`), OPC diagnostic endpoint (`/api/opc/test`), and real-time telemetry streaming at `http://localhost:8080/api/telemetry`.
- **Steady-State Benchmark Excel Model**: Complete 10-sheet dynamic flowsheet spreadsheet (`Cement_Kiln_Steady_State_Simulation_280TPH.xlsx`) with 295 formula-linked mass & heat balance calculations.

---

## 🛠️ Installation

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/ranjanoa/Limekilnsim.git
cd Limekilnsim

# Install requirements
pip install -r requirements.txt
```

---

## 🏃 Running the Application

### 1. Full Master Server (Web HMI + Physics Engine + OPC UA Server)

```bash
python server.py
# or on Windows with py launcher:
py server.py
```

Then open your browser at:
👉 **`http://localhost:8080/index.html`**

### 2. Standalone Server Mode (Without OPC UA)

```bash
python server.py --mode standalone
```

### 3. OPC UA Client Bridge Mode

To connect the simulator to an existing external industrial OPC UA server:

```bash
python server.py --mode client
```

### 4. Running Validation Runner Benchmark

```bash
python optimizer_validation_runner.py
```

---

## 📂 Repository Structure

```
├── config/
│   └── plant_config.json          # Plant geometry, nominal setpoints & PID parameters
├── engine/
│   └── first_principles_engine.py # Coupled ODE dynamic solver & kinetics
├── interfaces/
│   ├── opc_ua_server.py           # Industrial OPC UA Server
│   ├── opc_ua_client_bridge.py    # OPC UA Client Bridge
│   └── optimizer_client_demo.py   # Sample client connecting to the OPC UA node tree
├── simulator/                     # Web HMI Frontend
│   ├── index.html                 # Control room HMI dashboard
│   ├── style.css                  # Industrial SCADA UI styling
│   ├── app.js                     # UI state machine & telemetry polling
│   ├── physics.js                 # In-browser physics solver (standalone mode)
│   └── controllers.js             # PID and process loops
├── server.py                      # Master multi-threaded runner & REST API
├── requirements.txt               # Python package dependencies
└── README.md
```
