# Smart Manufacturing Digital Twin — Schneider Electric Yuva Yodha 2026

**Digital Twin & Energy Intelligence Software Prototype**  
*Built for the Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric)*

---

## 🏭 Executive Overview

This repository contains the **Digital Twin simulation engine** for an SME Smart Manufacturing energy-intelligence system. In modern industrial operations, physical hardware access can be constrained or dangerous for testing edge-case failures. This software prototype acts as a **high-fidelity virtual factory**, continuously generating:

1. **Physical Sensor Readings (`sensor_readings`)**: Simulated real-world machine sensors (Power in kW, Vibration in mm/s RMS, and Temperature in °C) reflecting operational noise and realistic physical variations.
2. **Digital Twin Expectations (`twin_predictions`)**: Clean, physics-based baseline predictions of what each machine *should* be consuming and exhibiting under the current factory load context.
3. **Anomaly & Fault Detection Mechanism**: The live divergence between the twin's expectation and the physical sensor reading serves as the primary signal that powers predictive maintenance, catching developing faults before catastrophic breakdown occurs.
4. **Time-of-Day (ToD) Energy Scheduling (`schedules`)**: Production windows matched to tariff bands (off-peak / cheap vs peak / expensive) and solar generation availability (09:00 - 16:00).
5. **Bureau of Energy Efficiency (BEE) Benchmarks (`audit_results`)**: Specific Energy Consumption (SEC) tracking vs Indian national standards.
6. **Carbon Footprint Tracking (`emissions_log`)**: Segregated solar vs grid energy consumption with Indian grid CO2 emission factors (0.82 kg CO2 / kWh).

All data streams directly into a cloud **Supabase** PostgreSQL database, feeding the accompanying React monitoring dashboard in real time.

---

## 📁 Repository Structure

```text
digital-twin/
│
├── config.py                 # Centralized configuration (credentials, machine baselines, fault settings)
├── main.py                   # SimPy-powered core simulation engine (generates & writes live data)
├── visualize.py              # Proof visualization script (queries Supabase & generates proof charts)
├── requirements.txt          # Python package dependencies
├── README.md                 # Setup, architecture, and run instructions
│
├── compressor_fault_demo.png # 300 DPI proof chart: Vibration anomaly divergence
└── compressor_power_demo.png # 300 DPI proof chart: Power draw excess & energy loss
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+ (Tested on Python 3.13)
- An active internet connection (to connect to the Supabase cloud instance)

### 1. Clone & Enter Directory
```bash
cd "digital twin"
```

### 2. Install Dependencies
Install all required libraries via `pip`:
```bash
pip install -r requirements.txt
```

*Packages installed:*
- `supabase`: Official Python client for real-time cloud database synchronization.
- `simpy`: Event-driven discrete simulation engine driving the virtual factory clock.
- `numpy`: Numerical calculations and Gaussian sensor noise generation.
- `matplotlib`: High-resolution proof chart rendering.
- `colorama`: Cross-platform highlighted ANSI terminal output for live demonstrations.
- `python-dateutil`: ISO timestamp parsing and chronological alignment.

---

## 🚀 Running the Digital Twin Simulation

### 1. Start the Simulation Engine
Execute the following command in your terminal:
```bash
python main.py
```

### 2. What Happens During Execution
1. **Startup Handshake**:
   - Connects to Supabase and verifies table connectivity.
   - Automatically seeds production schedules (`schedules`) demonstrating tariff load shifting (e.g., scheduling the energy-intensive Furnace during cheap off-peak night hours).
   - Seeds BEE energy audit benchmarks (`audit_results`) for SME efficiency scoring.
2. **Real-Time Simulation Loop**:
   - The SimPy clock ticks in 1-minute simulated intervals (with a 2-second real-time pacing delay for live demo readability).
   - Simulates 3 industrial assets:
     - **Motor_1**: Induction motor running a conveyor drive.
     - **Compressor_1**: Screw compressor powering pneumatic production lines.
     - **Furnace_1**: Induction melting unit with high thermal and power requirements.
   - Calculates time-of-day load curves (overnight low, morning ramp, afternoon peak).
   - Evaluates expected twin predictions and physical sensor readings with Gaussian noise.
   - Computes live vibration deviation:
     $$\text{Deviation \%} = \frac{|\text{Actual} - \text{Expected}|}{\text{Expected}} \times 100$$
   - Flags any deviation exceeding **15%** in bright red in the console.
   - Aggregates energy consumption every 10 steps and logs CO2 emissions.
3. **Graceful Stopping**:
   - Press `Ctrl + C` at any time to halt the simulation. All streamed data is safely persisted in Supabase.

---

## 🔍 Proof Visualization & Slide Charts

Once the simulation has run through the fault injection phase (e.g., 45-60 steps), run the visualization script to generate presentation-grade proof charts:

```bash
python visualize.py
```

### Generated Proof Charts:
- **`compressor_fault_demo.png`** (300 DPI):
  - Displays **Expected Vibration** (navy dashed line) alongside **Actual Sensor Reading** (red solid line).
  - Annotates the exact moment of **Fault Injection** (developing bearing wear).
  - Highlights the **Fault Divergence Zone** in semi-transparent red shading.
- **`compressor_power_demo.png`** (300 DPI):
  - Illustrates the parasitic energy loss and excess kW draw induced by the mechanical defect.

Both PNG files are saved directly in the project root and can be dropped directly into hackathon pitch decks and jury presentation slides.

---

## 🛠️ Tuning Simulation & Fault Parameters (`config.py`)

All core behavior can be adjusted in [`config.py`](config.py) without touching the engine logic:

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `STEP_REALTIME_SECONDS` | `2.0` | Real-time pause per step (set to `0.0` for instant batch backfill). |
| `FAULT_INJECTION_STEP` | `40` | Simulated step at which the fault starts developing. |
| `FAULT_MACHINE` | `"Compressor_1"` | Target machine for fault simulation. |
| `FAULT_GROWTH_RATE` | `0.035` | Compounding drift rate (+3.5% per step relative to expected). |
| `DEVIATION_ALERT_THRESHOLD_PERCENT` | `15.0` | Deviation percentage that triggers terminal warnings. |
| `NOISE_STD_FRACTION_POWER` | `0.04` | Standard deviation of Gaussian sensor noise for power (~4%). |
| `NOISE_STD_FRACTION_VIBRATION`| `0.04` | Standard deviation of Gaussian sensor noise for vibration (~4%).|
| `GRID_CO2_PER_KWH` | `0.82` | Indian grid emission factor (kg CO2 / kWh). |

---

## 📊 Database Schema Alignment

The simulation writes directly to the existing Supabase PostgreSQL tables:

- **`sensor_readings`**: `id`, `factory_id`, `machine_id`, `timestamp`, `power_kw`, `vibration`, `temperature`
- **`twin_predictions`**: `id`, `factory_id`, `machine_id`, `timestamp`, `expected_power`, `expected_vibration`, `load_context`
- **`schedules`**: `id`, `factory_id`, `machine_id`, `scheduled_start`, `scheduled_end`, `tariff_band`, `solar_available`
- **`audit_results`**: `id`, `factory_id`, `machine_id`, `sec_actual`, `sec_bee_benchmark`, `recommended_action`, `priority_rank`
- **`emissions_log`**: `id`, `factory_id`, `timestamp`, `grid_kwh`, `solar_kwh`, `co2_kg`

---

## 🏆 Hackathon Alignment (Schneider Electric Yuva Yodha 2026)

- **Believable Digital Twin**: Demonstrates mathematical physics-informed baseline modeling vs empirical sensor telemetry.
- **Predictive Fault Warning**: Detects micro-vibrations and energy drag well before catastrophic machine failure.
- **Sustainability & Decarbonization**: Incorporates CEA grid carbon factors and demonstrates real-time solar utilization.
- **Grid Stability & Load Shifting**: Demonstrates intelligent scheduling of heavy inductive loads (Furnace) during off-peak tariff hours.
