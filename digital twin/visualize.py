"""
Proof & Visualization Generator for Smart Manufacturing Digital Twin
Yuva Yodha Energy Tech Hackathon 2026 (Schneider Electric)

Queries sensor_readings and twin_predictions from Supabase for Compressor_1,
analyzes the divergence between expected physics baseline and actual sensor values,
and produces high-resolution presentation charts:
  1. compressor_fault_demo.png (Vibration anomaly divergence)
  2. compressor_power_demo.png (Power consumption anomaly divergence)
"""

import sys
from datetime import datetime

# Reconfigure stdout/stderr for cross-platform UTF-8 safety on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dateutil import parser
from colorama import Fore, Style, init

import config

init(autoreset=True)

try:
    from supabase import create_client, Client
except ImportError:
    print(Fore.RED + "Error: 'supabase' package is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


def fetch_twin_and_sensor_data(client: Client, target_machine: str = "Compressor_1", limit: int = 100):
    """
    Fetch the latest recorded rows for target_machine from both tables.
    Returns sorted chronological lists of readings and predictions.
    """
    print(Fore.CYAN + f"Fetching up to {limit} records for {target_machine} from Supabase...")

    # Fetch sensor readings
    sensor_res = (
        client.table("sensor_readings")
        .select("*")
        .eq("factory_id", config.FACTORY_ID)
        .eq("machine_id", target_machine)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )

    # Fetch twin predictions
    prediction_res = (
        client.table("twin_predictions")
        .select("*")
        .eq("factory_id", config.FACTORY_ID)
        .eq("machine_id", target_machine)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )

    sensors = sensor_res.data or []
    predictions = prediction_res.data or []

    if not sensors or not predictions:
        print(Fore.RED + f"\n[NO DATA] Found {len(sensors)} sensor readings and {len(predictions)} twin predictions.")
        print(Fore.YELLOW + "Please run 'python main.py' first and let it run for at least 40-50 steps to generate data.\n")
        sys.exit(1)

    # Reverse to chronological ascending order
    sensors.reverse()
    predictions.reverse()

    # Map predictions by timestamp for precise 1-to-1 matching
    pred_map = {row["timestamp"]: row for row in predictions}

    paired_data = []
    for s_row in sensors:
        ts = s_row["timestamp"]
        if ts in pred_map:
            p_row = pred_map[ts]
            paired_data.append({
                "timestamp": parser.isoparse(ts),
                "actual_vibration": float(s_row["vibration"]),
                "expected_vibration": float(p_row["expected_vibration"]),
                "actual_power": float(s_row["power_kw"]),
                "expected_power": float(p_row["expected_power"]),
                "temperature": float(s_row.get("temperature", 0.0)),
                "load_context": p_row.get("load_context", ""),
            })

    # If exact timestamps had slight drift, pair by index
    if not paired_data:
        min_len = min(len(sensors), len(predictions))
        for i in range(min_len):
            s_row = sensors[i]
            p_row = predictions[i]
            paired_data.append({
                "timestamp": parser.isoparse(s_row["timestamp"]),
                "actual_vibration": float(s_row["vibration"]),
                "expected_vibration": float(p_row["expected_vibration"]),
                "actual_power": float(s_row["power_kw"]),
                "expected_power": float(p_row["expected_power"]),
                "temperature": float(s_row.get("temperature", 0.0)),
                "load_context": p_row.get("load_context", ""),
            })

    print(Fore.GREEN + f"  [OK] Successfully retrieved and paired {len(paired_data)} records for {target_machine}.")
    return paired_data


def detect_fault_injection_point(paired_data):
    """
    Identifies the index/timestamp where fault injection took effect.
    Looks for the point where actual vibration begins significant compounding divergence.
    """
    for idx, item in enumerate(paired_data):
        dev = abs(item["actual_vibration"] - item["expected_vibration"]) / item["expected_vibration"]
        if dev > 0.12 and idx >= 5:  # sustained deviation above 12%
            return idx, item["timestamp"]

    # Fallback to config FAULT_INJECTION_STEP if available
    if len(paired_data) > config.FAULT_INJECTION_STEP:
        return config.FAULT_INJECTION_STEP, paired_data[config.FAULT_INJECTION_STEP]["timestamp"]
    return None, None


def plot_vibration_proof(paired_data, fault_idx, fault_time, output_filename="compressor_fault_demo.png"):
    """
    Generate the primary vibration proof chart with high resolution.
    Visualizes the divergence between twin expectations and actual sensor readings.
    """
    timestamps = [d["timestamp"] for d in paired_data]
    actual_vib = [d["actual_vibration"] for d in paired_data]
    expected_vib = [d["expected_vibration"] for d in paired_data]

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=300)

    # Plot Expected vs Actual
    line_exp, = ax.plot(
        timestamps,
        expected_vib,
        label="Expected (twin prediction)",
        color="#0F2942",
        linestyle="--",
        linewidth=2.2,
        alpha=0.9,
    )
    line_act, = ax.plot(
        timestamps,
        actual_vib,
        label="Actual (sensor reading)",
        color="#E53935",
        linestyle="-",
        linewidth=2.4,
        alpha=0.95,
    )

    # Shade the divergence region to clearly highlight the fault zone
    ax.fill_between(
        timestamps,
        actual_vib,
        expected_vib,
        where=[a > e for a, e in zip(actual_vib, expected_vib)],
        color="#EF5350",
        alpha=0.18,
        label="Fault Divergence Zone",
    )

    # Mark fault injection point
    if fault_time:
        ax.axvline(
            x=fault_time,
            color="#616161",
            linestyle=":",
            linewidth=2.0,
            alpha=0.85,
        )
        # Callout text annotation
        y_max = max(actual_vib)
        ax.annotate(
            "Fault Injected\n(Developing Bearing Wear)",
            xy=(fault_time, expected_vib[fault_idx] if fault_idx < len(expected_vib) else y_max * 0.5),
            xytext=(15, 40),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5),
            fontsize=10,
            fontweight="bold",
            color="#212121",
            backgroundcolor="#FFF3E0",
            bbox=dict(boxstyle="round,pad=0.4", fc="#FFF3E0", ec="#FFB74D", lw=1.2),
        )

    # Aesthetics and labels
    ax.set_title(
        "Digital Twin: Expected vs Actual (Compressor_1)",
        fontsize=16,
        fontweight="bold",
        pad=15,
        color="#1A202C",
    )
    ax.set_xlabel("Simulated Factory Time", fontsize=12, fontweight="semibold", labelpad=10)
    ax.set_ylabel("Vibration Velocity (mm/s RMS)", fontsize=12, fontweight="semibold", labelpad=10)

    # Format timestamp on x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")

    # Clean grid and borders
    ax.grid(True, linestyle="--", alpha=0.5, color="#CFD8DC")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#90A4AE")

    # Legend
    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="#B0BEC5",
        framealpha=0.95,
        fontsize=11,
    )

    # Subtitle / Hackathon badge
    plt.figtext(
        0.5,
        0.01,
        "Yuva Yodha Energy Tech Hackathon 2026 | Schneider Electric Digital Twin Prototype",
        wrap=True,
        horizontalalignment="center",
        fontsize=9,
        color="#78909C",
        fontstyle="italic",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.savefig(output_filename, dpi=300)
    plt.close()
    print(Fore.GREEN + Style.BRIGHT + f"  [OK] Saved vibration proof chart to: {output_filename} (300 DPI)")


def plot_power_proof(paired_data, fault_idx, fault_time, output_filename="compressor_power_demo.png"):
    """
    Generate the secondary power proof chart showing how power increases with mechanical drag.
    """
    timestamps = [d["timestamp"] for d in paired_data]
    actual_power = [d["actual_power"] for d in paired_data]
    expected_power = [d["expected_power"] for d in paired_data]

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(12, 6.0), dpi=300)

    # Plot Expected vs Actual Power
    ax.plot(
        timestamps,
        expected_power,
        label="Expected Power (twin baseline, kW)",
        color="#00695C",
        linestyle="--",
        linewidth=2.2,
        alpha=0.9,
    )
    ax.plot(
        timestamps,
        actual_power,
        label="Actual Power (sensor reading, kW)",
        color="#D84315",
        linestyle="-",
        linewidth=2.2,
        alpha=0.95,
    )

    # Shade the difference
    ax.fill_between(
        timestamps,
        actual_power,
        expected_power,
        where=[a > e for a, e in zip(actual_power, expected_power)],
        color="#FF8A65",
        alpha=0.2,
        label="Excess Energy Drain (Friction Loss)",
    )

    if fault_time:
        ax.axvline(
            x=fault_time,
            color="#616161",
            linestyle=":",
            linewidth=2.0,
            alpha=0.85,
        )
        ax.annotate(
            "Fault Injected\n(Excess kW Draw)",
            xy=(fault_time, expected_power[fault_idx] if fault_idx < len(expected_power) else max(actual_power) * 0.7),
            xytext=(15, 30),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5),
            fontsize=10,
            fontweight="bold",
            color="#212121",
            backgroundcolor="#FFF3E0",
            bbox=dict(boxstyle="round,pad=0.4", fc="#FFF3E0", ec="#FFB74D", lw=1.2),
        )

    ax.set_title(
        "Digital Twin: Power Consumption vs Expected Baseline (Compressor_1)",
        fontsize=15,
        fontweight="bold",
        pad=15,
        color="#1A202C",
    )
    ax.set_xlabel("Simulated Factory Time", fontsize=12, fontweight="semibold", labelpad=10)
    ax.set_ylabel("Power Consumption (kW)", fontsize=12, fontweight="semibold", labelpad=10)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")

    ax.grid(True, linestyle="--", alpha=0.5, color="#CFD8DC")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#90A4AE")

    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="#B0BEC5",
        framealpha=0.95,
        fontsize=11,
    )

    plt.figtext(
        0.5,
        0.01,
        "Yuva Yodha Energy Tech Hackathon 2026 | Schneider Electric Digital Twin Prototype",
        wrap=True,
        horizontalalignment="center",
        fontsize=9,
        color="#78909C",
        fontstyle="italic",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.savefig(output_filename, dpi=300)
    plt.close()
    print(Fore.GREEN + Style.BRIGHT + f"  [OK] Saved power proof chart to: {output_filename} (300 DPI)")


def main():
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 70)
    print(Fore.CYAN + Style.BRIGHT + "  DIGITAL TWIN PROOF GENERATOR — VISUALIZE.PY")
    print(Fore.CYAN + Style.BRIGHT + "=" * 70)

    # Initialize Supabase client
    try:
        client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    except Exception as e:
        print(Fore.RED + f"Error connecting to Supabase: {e}")
        sys.exit(1)

    # Retrieve data
    paired_data = fetch_twin_and_sensor_data(client, target_machine="Compressor_1", limit=100)

    # Locate fault injection transition
    fault_idx, fault_time = detect_fault_injection_point(paired_data)

    # Plot charts
    plot_vibration_proof(paired_data, fault_idx, fault_time, "compressor_fault_demo.png")
    plot_power_proof(paired_data, fault_idx, fault_time, "compressor_power_demo.png")

    print(Fore.CYAN + Style.BRIGHT + "\nAll proof charts successfully generated at 300 DPI.")
    print(Fore.WHITE + "You can paste 'compressor_fault_demo.png' and 'compressor_power_demo.png' directly into your presentation slides.\n")


if __name__ == "__main__":
    main()
