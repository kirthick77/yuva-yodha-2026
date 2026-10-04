"""
Smart Manufacturing Digital Twin - Core Simulation Engine
Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric)

Simulates a factory environment with 3 core machines (Motor, Compressor, Furnace).
Generates physical sensor readings alongside the Digital Twin's expected baseline predictions.
Injects mechanical fault drift to demonstrate live predictive fault detection,
energy scheduling, solar optimization, BEE benchmarking, and CO2 emissions tracking.
"""

import sys
import time
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Reconfigure stdout/stderr for cross-platform UTF-8 safety on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import simpy
from colorama import Fore, Back, Style, init

import config

# Initialize colorama for cross-platform ANSI terminal styling
init(autoreset=True)

try:
    from supabase import create_client, Client
except ImportError:
    print(Fore.RED + "Error: 'supabase' package is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


# --------------------------------------------------------------------------
# DATABASE CONNECTION & INITIALIZATION
# --------------------------------------------------------------------------
def init_supabase() -> Client:
    """Initialize and verify connection to Supabase client."""
    try:
        client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        # Quick ping test on sensor_readings
        client.table("sensor_readings").select("id").limit(1).execute()
        return client
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + "\n[ERROR] Failed to connect to Supabase database!")
        print(Fore.YELLOW + f"Details: {e}")
        print(Fore.YELLOW + "Check your network connection and SUPABASE_URL / SUPABASE_KEY in config.py.\n")
        sys.exit(1)


def seed_schedules(client: Client):
    """
    Seed initial production schedules into the database.
    Demonstrates tariff-aware load shifting (e.g. Furnace scheduled for cheap off-peak hours).
    """
    print(Fore.CYAN + "[INIT] Seeding production schedules into Supabase...")
    base_date = config.SIMULATION_START_TIME.date()

    # Define scheduled windows
    schedules_data = [
        {
            "factory_id": config.FACTORY_ID,
            "machine_id": "Motor_1",
            "scheduled_start": datetime(base_date.year, base_date.month, base_date.day, 9, 0, tzinfo=timezone.utc).isoformat(),
            "scheduled_end": datetime(base_date.year, base_date.month, base_date.day, 17, 0, tzinfo=timezone.utc).isoformat(),
            "tariff_band": "mid",
            "solar_available": True,
        },
        {
            "factory_id": config.FACTORY_ID,
            "machine_id": "Compressor_1",
            "scheduled_start": datetime(base_date.year, base_date.month, base_date.day, 6, 0, tzinfo=timezone.utc).isoformat(),
            "scheduled_end": datetime(base_date.year, base_date.month, base_date.day, 22, 0, tzinfo=timezone.utc).isoformat(),
            "tariff_band": "mid",
            "solar_available": True,
        },
        {
            "factory_id": config.FACTORY_ID,
            "machine_id": "Furnace_1",
            "scheduled_start": datetime(base_date.year, base_date.month, base_date.day, 22, 0, tzinfo=timezone.utc).isoformat(),
            "scheduled_end": (datetime(base_date.year, base_date.month, base_date.day, 6, 0, tzinfo=timezone.utc) + timedelta(days=1)).isoformat(),
            "tariff_band": "cheap",
            "solar_available": False,
        },
    ]

    try:
        # Check if already present for today to avoid duplicate clutter
        res = client.table("schedules").select("id").eq("factory_id", config.FACTORY_ID).limit(3).execute()
        if not res.data or len(res.data) < 3:
            client.table("schedules").insert(schedules_data).execute()
            print(Fore.GREEN + f"  [OK] Successfully seeded {len(schedules_data)} machine schedules.")
        else:
            print(Fore.LIGHTBLACK_EX + "  [INFO] Schedules already initialized for factory_demo.")
    except Exception as err:
        print(Fore.YELLOW + f"  [WARNING] Could not insert schedules: {err}")


def seed_bee_audit_benchmarks(client: Client):
    """
    Seed Bureau of Energy Efficiency (BEE) benchmark and energy audit data.
    Allows SME operators to benchmark Specific Energy Consumption (SEC) vs national norms.
    """
    try:
        res = client.table("audit_results").select("id").eq("factory_id", config.FACTORY_ID).limit(1).execute()
        if not res.data:
            print(Fore.CYAN + "[INIT] Seeding BEE Energy Audit benchmarks into Supabase...")
            audit_rows = []
            for item in config.BEE_BENCHMARKS:
                audit_rows.append({
                    "factory_id": config.FACTORY_ID,
                    "machine_id": item["machine_id"],
                    "sec_actual": item["sec_actual"],
                    "sec_bee_benchmark": item["sec_bee_benchmark"],
                    "recommended_action": item["recommended_action"],
                    "priority_rank": item["priority_rank"],
                })
            client.table("audit_results").insert(audit_rows).execute()
            print(Fore.GREEN + f"  [OK] Successfully seeded {len(audit_rows)} BEE audit benchmark rows.")
    except Exception as err:
        print(Fore.YELLOW + f"  [WARNING] Could not seed audit results: {err}")


# --------------------------------------------------------------------------
# LOAD MULTIPLIER & PHYSICAL TWIN MODELS
# --------------------------------------------------------------------------
def compute_load_multiplier(simulated_minute: int) -> float:
    """
    STEP 1: Compute a realistic time-of-day load curve for a 24-hour cycle (1440 mins).
    - Off-peak overnight: ~0.70x
    - Morning ramp-up (starts ~07:30 - 08:00)
    - Afternoon peak (11:00 - 15:30): ~1.15x - 1.25x
    - Evening ramp-down: ~0.80x
    """
    minute_in_day = simulated_minute % 1440
    hour = minute_in_day / 60.0

    # Smooth multi-harmonic sine wave mimicking factory shift cycles
    # Peak centered around 13:30 (1:30 PM), trough around 03:30 AM
    theta = (hour - 13.5) * (2.0 * math.pi / 24.0)
    base = 0.98 + 0.26 * math.cos(theta) - 0.04 * math.cos(2.0 * theta)
    return round(float(np.clip(base, 0.68, 1.28)), 4)


def get_load_context(simulated_minute: int) -> str:
    """Returns load context category based on simulated hour."""
    hour = (simulated_minute % 1440) / 60.0
    if 8.0 <= hour < 18.0:
        return "working_hours"
    elif 18.0 <= hour < 22.0:
        return "evening_peak"
    else:
        return "off_hours"


def is_solar_window(simulated_minute: int) -> bool:
    """Check if simulated time falls within productive solar hours (09:00 - 16:00)."""
    hour = (simulated_minute % 1440) / 60.0
    return config.SOLAR_START_HOUR <= hour < config.SOLAR_END_HOUR


# --------------------------------------------------------------------------
# STEP-BY-STEP CALCULATION ENGINE
# --------------------------------------------------------------------------
def simulate_machine_step(
    machine_id: str,
    spec: Dict[str, Any],
    simulated_step: int,
    load_mult: float,
    current_temp_state: float,
) -> Dict[str, Any]:
    """
    Simulates a single step for a given machine:
    - Expected twin prediction (clean, physics baseline)
    - Actual sensor reading (Gaussian noise + physical drift)
    - Compounding fault injection if active
    - Deviation percentage calculation
    """
    # STEP 2: Expected (Twin Prediction) Values
    base_p = spec["baseline_power_kw"]
    base_v = spec["baseline_vibration"]
    base_t = spec["baseline_temperature"]
    vib_sens = spec["vibration_sensitivity"]
    temp_sens = spec["temp_sensitivity"]

    expected_power = round(base_p * load_mult, 3)
    expected_vibration = round(base_v * (1.0 + (load_mult - 1.0) * vib_sens), 3)

    # STEP 3: Actual (Sensor) Values with Gaussian Noise
    noise_p = np.random.normal(0, config.NOISE_STD_FRACTION_POWER * expected_power)
    noise_v = np.random.normal(0, config.NOISE_STD_FRACTION_VIBRATION * expected_vibration)
    actual_power = max(0.1, expected_power + noise_p)
    actual_vibration = max(0.1, expected_vibration + noise_v)

    # Temperature thermal inertia (slowly approaches target temperature with noise)
    target_temp = base_t + (load_mult - 1.0) * temp_sens
    # 20% convergence towards target per step plus thermal noise
    new_temp = current_temp_state + 0.20 * (target_temp - current_temp_state) + np.random.normal(0, config.NOISE_STD_TEMPERATURE)
    actual_temp = max(15.0, new_temp)

    # STEP 4: Fault Injection Mechanism
    fault_active = False
    fault_percent_added = 0.0

    if machine_id == config.FAULT_MACHINE and simulated_step >= config.FAULT_INJECTION_STEP:
        fault_active = True
        fault_step_idx = simulated_step - config.FAULT_INJECTION_STEP + 1
        # Compounding growth per step relative to expected baseline
        # e.g. Step 1: +3.5%, Step 2: +7.1%, Step 10: +41.0%
        fault_growth_factor = ((1.0 + config.FAULT_GROWTH_RATE) ** fault_step_idx) - 1.0
        fault_percent_added = fault_growth_factor * 100.0

        extra_vibration = expected_vibration * fault_growth_factor
        extra_power = expected_power * (fault_growth_factor * 0.70)  # power rises with friction
        extra_temp = fault_step_idx * 0.35  # friction generates thermal heat

        actual_vibration += extra_vibration
        actual_power += extra_power
        actual_temp += extra_temp

    # Round outputs for database cleanliness
    actual_power = round(actual_power, 3)
    actual_vibration = round(actual_vibration, 3)
    actual_temp = round(actual_temp, 2)

    # STEP 5: Percent Deviation from Expected
    deviation_percent = abs(actual_vibration - expected_vibration) / expected_vibration * 100.0

    return {
        "machine_id": machine_id,
        "expected_power": expected_power,
        "expected_vibration": expected_vibration,
        "actual_power": actual_power,
        "actual_vibration": actual_vibration,
        "actual_temperature": actual_temp,
        "deviation_percent": round(deviation_percent, 2),
        "fault_active": fault_active,
        "fault_percent_added": round(fault_percent_added, 1),
    }


# --------------------------------------------------------------------------
# SIMPY SIMULATION PROCESS
# --------------------------------------------------------------------------
def factory_simulation_process(env: simpy.Environment, client: Client):
    """
    Main SimPy simulation process.
    Advances 1 simulated minute per step and coordinates calculations, console
    logging, and writes to Supabase.
    """
    # Track current temperatures for thermal continuity
    temp_states = {
        m_id: spec["baseline_temperature"]
        for m_id, spec in config.MACHINES.items()
    }

    # Energy accumulator for 10-step emissions logging
    accumulated_solar_kwh = 0.0
    accumulated_grid_kwh = 0.0

    step_counter = 0

    print(Fore.GREEN + Style.BRIGHT + "\n" + "=" * 80)
    print(Fore.GREEN + Style.BRIGHT + "  SMART MANUFACTURING DIGITAL TWIN - LIVE SIMULATION ACTIVE")
    print(Fore.GREEN + Style.BRIGHT + "  Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric)")
    print(Fore.GREEN + Style.BRIGHT + "=" * 80)
    print(Fore.WHITE + f"  Factory ID            : {config.FACTORY_ID}")
    print(Fore.WHITE + f"  Real-time delay/step  : {config.STEP_REALTIME_SECONDS}s")
    print(Fore.WHITE + f"  Fault injection target: {config.FAULT_MACHINE} at Step {config.FAULT_INJECTION_STEP} (+{config.FAULT_GROWTH_RATE*100}% compounding)")
    print(Fore.WHITE + f"  Anomaly threshold     : >{config.DEVIATION_ALERT_THRESHOLD_PERCENT}% vibration deviation")
    print(Fore.GREEN + Style.BRIGHT + "=" * 80 + "\n")

    while True:
        step_counter += 1
        simulated_time = config.SIMULATION_START_TIME + timedelta(minutes=step_counter)
        simulated_iso = simulated_time.isoformat()
        sim_time_str = simulated_time.strftime("%Y-%m-%d %H:%M UTC")

        load_mult = compute_load_multiplier(step_counter)
        load_ctx = get_load_context(step_counter)
        solar_in_effect = is_solar_window(step_counter)

        # Print step banner
        step_hdr = (
            f" [STEP {step_counter:03d}] {sim_time_str} | "
            f"Load Multiplier: {load_mult:.2f}x ({load_ctx}) | "
            f"Solar: {'ACTIVE (0kg CO2)' if solar_in_effect else 'GRID OFF-SUN'}"
        )
        print(Fore.CYAN + Style.BRIGHT + "-" * 80)
        print(Fore.CYAN + Style.BRIGHT + step_hdr)
        print(Fore.CYAN + Style.BRIGHT + "-" * 80)

        # Notify exactly when fault injection begins
        if step_counter == config.FAULT_INJECTION_STEP:
            print(
                Back.RED + Fore.WHITE + Style.BRIGHT +
                f" >>> [FAULT INJECTION STARTED] {config.FAULT_MACHINE} — "
                f"simulating developing mechanical fault from step {config.FAULT_INJECTION_STEP} onward <<< "
            )

        step_sensor_rows = []
        step_prediction_rows = []
        step_total_power_kw = 0.0

        for m_id, spec in config.MACHINES.items():
            result = simulate_machine_step(
                machine_id=m_id,
                spec=spec,
                simulated_step=step_counter,
                load_mult=load_mult,
                current_temp_state=temp_states[m_id],
            )
            temp_states[m_id] = result["actual_temperature"]
            step_total_power_kw += result["actual_power"]

            # STEP 5: Live Deviation Flagging in Terminal
            dev = result["deviation_percent"]
            act_v = result["actual_vibration"]
            exp_v = result["expected_vibration"]
            act_p = result["actual_power"]
            exp_p = result["expected_power"]
            act_t = result["actual_temperature"]

            if dev >= config.DEVIATION_ALERT_THRESHOLD_PERCENT:
                # Highlighted anomaly warning
                print(
                    Fore.RED + Style.BRIGHT +
                    f"  [FAULT DEVIATION] {m_id:13s} — vibration {dev:5.1f}% above expected "
                    f"(actual={act_v:5.2f} mm/s, expected={exp_v:5.2f} mm/s) | "
                    f"Power: {act_p:5.1f}kW (exp {exp_p:5.1f}kW) | Temp: {act_t:5.1f}°C"
                )
            else:
                # Normal operational status
                print(
                    Fore.LIGHTGREEN_EX +
                    f"  [NOMINAL TWIN]   {m_id:13s} — Power: {act_p:5.1f}/{exp_p:5.1f} kW | "
                    f"Vibration: {act_v:4.2f}/{exp_v:4.2f} mm/s (dev: {dev:4.1f}%) | "
                    f"Temp: {act_t:5.1f}°C"
                )

            # Database write payloads
            step_sensor_rows.append({
                "factory_id": config.FACTORY_ID,
                "machine_id": m_id,
                "timestamp": simulated_iso,
                "power_kw": result["actual_power"],
                "vibration": result["actual_vibration"],
                "temperature": result["actual_temperature"],
            })

            step_prediction_rows.append({
                "factory_id": config.FACTORY_ID,
                "machine_id": m_id,
                "timestamp": simulated_iso,
                "expected_power": result["expected_power"],
                "expected_vibration": result["expected_vibration"],
                "load_context": load_ctx,
            })

        # STEP 6: Execute Supabase Database Writes
        try:
            client.table("sensor_readings").insert(step_sensor_rows).execute()
            client.table("twin_predictions").insert(step_prediction_rows).execute()
        except Exception as err:
            print(Fore.YELLOW + f"  [DB WRITE ERROR] Step {step_counter}: {err}")

        # Energy consumption in kWh for this 1-minute step: kW * (1/60 hours)
        step_kwh = step_total_power_kw * (1.0 / 60.0)
        if solar_in_effect:
            accumulated_solar_kwh += step_kwh
        else:
            accumulated_grid_kwh += step_kwh

        # EMISSIONS DATA: Written every 10 simulated steps
        if step_counter % config.EMISSIONS_LOG_INTERVAL_STEPS == 0:
            co2_emissions = round(accumulated_grid_kwh * config.GRID_CO2_PER_KWH, 3)
            solar_logged = round(accumulated_solar_kwh, 3)
            grid_logged = round(accumulated_grid_kwh, 3)

            emissions_entry = {
                "factory_id": config.FACTORY_ID,
                "timestamp": simulated_iso,
                "grid_kwh": grid_logged,
                "solar_kwh": solar_logged,
                "co2_kg": co2_emissions,
            }

            try:
                client.table("emissions_log").insert([emissions_entry]).execute()
                print(
                    Fore.MAGENTA + Style.BRIGHT +
                    f"  [EMISSIONS LOG] Steps {step_counter-9:02d}-{step_counter:02d}: "
                    f"Grid: {grid_logged:.2f} kWh | Solar: {solar_logged:.2f} kWh | "
                    f"CO2 Produced: {co2_emissions:.2f} kg"
                )
            except Exception as err:
                print(Fore.YELLOW + f"  [EMISSIONS LOG ERROR]: {err}")

            # Reset window accumulators
            accumulated_solar_kwh = 0.0
            accumulated_grid_kwh = 0.0

        # SimPy clock step & Realtime Pacing
        # Advance SimPy environment by 1 minute
        yield env.timeout(1)

        # Sleep for the configured real seconds so human spectators can watch
        if config.STEP_REALTIME_SECONDS > 0:
            time.sleep(config.STEP_REALTIME_SECONDS)


# --------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# --------------------------------------------------------------------------
def main():
    """Main startup orchestrator."""
    print(Fore.CYAN + Style.BRIGHT + "\nStarting Schneider Electric Digital Twin Engine...")
    supabase_client = init_supabase()
    print(Fore.GREEN + "[OK] Connected to Supabase successfully.")

    # Seed startup schedules and BEE audit data
    seed_schedules(supabase_client)
    seed_bee_audit_benchmarks(supabase_client)

    # Initialize SimPy Environment
    sim_env = simpy.Environment()
    sim_env.process(factory_simulation_process(sim_env, supabase_client))

    try:
        sim_env.run()
    except KeyboardInterrupt:
        print(Fore.YELLOW + Style.BRIGHT + "\n\n[SIMULATION STOPPED] Interrupted by user (Ctrl+C).")
        print(Fore.WHITE + "Data is safely stored in Supabase.")
        print(Fore.WHITE + "To generate proof charts, run: " + Fore.GREEN + "python visualize.py\n")


if __name__ == "__main__":
    main()
