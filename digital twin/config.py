"""
Configuration Module for Smart Manufacturing Digital Twin
Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric)

All tunable constants, machine baselines, simulation rates, and Supabase credentials
are centralized here for easy tuning during demonstrations and evaluations.
"""

from datetime import datetime, timezone, timedelta

# --------------------------------------------------------------------------
# SUPABASE CONNECTION CONFIGURATION
# --------------------------------------------------------------------------
SUPABASE_URL = "https://yguzfqsgkttohbxqwmnp.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlndXpmcXNna3R0b2hieHF3bW5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEwMTA0NzcsImV4cCI6MjEwNjU4NjQ3N30."
    "ajMjfIQZ4lShjI1LPtwJ9gOpoKypxuomQSUDJNa_lh4"
)

# --------------------------------------------------------------------------
# FACTORY & ASSET CONFIGURATION
# --------------------------------------------------------------------------
FACTORY_ID = "factory_demo"

# Machine definitions with physical operational baselines
MACHINES = {
    "Motor_1": {
        "name": "Induction Motor 1 (Conveyor Drive)",
        "baseline_power_kw": 5.0,
        "baseline_vibration": 2.0,      # mm/s RMS
        "baseline_temperature": 45.0,   # °C
        "vibration_sensitivity": 0.25,  # gentle scaling with load
        "temp_sensitivity": 8.0,
    },
    "Compressor_1": {
        "name": "Screw Air Compressor 1 (Pneumatic Line)",
        "baseline_power_kw": 12.0,
        "baseline_vibration": 3.5,      # mm/s RMS
        "baseline_temperature": 60.0,   # °C
        "vibration_sensitivity": 0.30,
        "temp_sensitivity": 12.0,
    },
    "Furnace_1": {
        "name": "Electric Induction Furnace 1 (Melting Unit)",
        "baseline_power_kw": 25.0,
        "baseline_vibration": 1.5,      # mm/s RMS (low mechanical vibration)
        "baseline_temperature": 180.0,  # °C
        "vibration_sensitivity": 0.15,
        "temp_sensitivity": 35.0,
    },
}

# --------------------------------------------------------------------------
# SIMULATION TIMING & PACING
# --------------------------------------------------------------------------
# Step delay in seconds: 2.0 to 3.0s makes live terminal demos easy to follow.
# Set to 0.0 for instant testing / batch data generation.
STEP_REALTIME_SECONDS = 2.0

# 1 simulation step = 1 simulated minute
STEP_SIMULATED_MINUTES = 1

# Simulation clock starting point: Midnight (00:00:00) UTC today
SIMULATION_START_TIME = datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
)

# --------------------------------------------------------------------------
# SENSOR NOISE CONFIGURATION
# --------------------------------------------------------------------------
# Gaussian noise standard deviation as a fraction of expected value (3% - 5%)
NOISE_STD_FRACTION_POWER = 0.04
NOISE_STD_FRACTION_VIBRATION = 0.04
NOISE_STD_TEMPERATURE = 0.6  # absolute °C fluctuation

# --------------------------------------------------------------------------
# FAULT INJECTION (THE DIGITAL TWIN PROOF MECHANISM)
# --------------------------------------------------------------------------
# At this step, the specified machine starts developing an anomalous drift.
FAULT_INJECTION_STEP = 40
FAULT_MACHINE = "Compressor_1"

# Compounding drift rate per step (3.5% = 0.035) added to actual reading
FAULT_GROWTH_RATE = 0.035

# Vibration deviation threshold to trigger terminal alerts
DEVIATION_ALERT_THRESHOLD_PERCENT = 15.0

# --------------------------------------------------------------------------
# ENERGY TARIFF & SOLAR WINDOWS
# --------------------------------------------------------------------------
# Peak & off-peak tariff definitions (typical industrial SME ToD tariffs in India)
# Solar hours: 09:00 to 16:00
SOLAR_START_HOUR = 9
SOLAR_END_HOUR = 16

# Carbon emission intensity for Indian power grid (kg CO2 per kWh)
# Central Electricity Authority (CEA) standard ~0.82 kg CO2/kWh
GRID_CO2_PER_KWH = 0.82
SOLAR_CO2_PER_KWH = 0.00

# How often to log aggregated carbon emissions (in simulated steps / minutes)
EMISSIONS_LOG_INTERVAL_STEPS = 10

# --------------------------------------------------------------------------
# BUREAU OF ENERGY EFFICIENCY (BEE) BENCHMARKS (AUDIT RESULTS)
# --------------------------------------------------------------------------
# Specific Energy Consumption (SEC) benchmarks: kWh / unit output
BEE_BENCHMARKS = [
    {
        "machine_id": "Compressor_1",
        "sec_actual": 0.78,
        "sec_bee_benchmark": 0.62,
        "recommended_action": "Inspect for compressed air leakage (>18% detected) & replace worn drive belt",
        "priority_rank": 1,
    },
    {
        "machine_id": "Motor_1",
        "sec_actual": 0.44,
        "sec_bee_benchmark": 0.38,
        "recommended_action": "Retrofit with IE4 Super Premium motor and install variable frequency drive (VFD)",
        "priority_rank": 2,
    },
    {
        "machine_id": "Furnace_1",
        "sec_actual": 1.18,
        "sec_bee_benchmark": 1.10,
        "recommended_action": "Schedule operations during night off-peak tariff band and inspect ceramic lining insulation",
        "priority_rank": 3,
    },
]
