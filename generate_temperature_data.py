"""
High-Low Temperature Cycling Test Data Generator
Generates 168-hour temperature cycling test data with 10-second sampling interval.

Configuration:
- Sampling interval: 10 seconds
- Total data points: 168h × 3600s/h ÷ 10s = 60,480
- Cycles: 21 complete cycles, each 8 hours
- Temperature range: -40°C (low) to 125°C (high)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
SAMPLE_INTERVAL_S = 10          # seconds between samples
TOTAL_HOURS = 168               # test duration in hours
CYCLE_HOURS = 8                 # hours per cycle
NUM_CYCLES = TOTAL_HOURS // CYCLE_HOURS  # 21 cycles

TOTAL_SAMPLES = TOTAL_HOURS * 3600 // SAMPLE_INTERVAL_S  # 60,480

# Temperature profile (°C)
TEMP_HIGH = 125.0
TEMP_LOW = -40.0
TEMP_AMBIENT = 25.0

# Phase durations (fraction of one cycle)
RAMP_UP_FRAC = 0.10    # 10% ramp up
SOAK_HIGH_FRAC = 0.30  # 30% high soak
RAMP_DOWN_FRAC = 0.10  # 10% ramp down
SOAK_LOW_FRAC = 0.30   # 30% low soak
RAMP_BACK_FRAC = 0.20  # 20% ramp back to ambient (end of last cycle)

# Noise model
NOISE_STD = 0.5        # °C  Gaussian noise
ALPHA_SMOOTH = 0.05    # exponential smoothing factor (thermal lag)

# ── Helper ─────────────────────────────────────────────────────────────────────

def cubic_ease(t: float) -> float:
    """Smooth s-curve ramp: 0→1 over t∈[0,1]."""
    return 3 * t ** 2 - 2 * t ** 3


def humidity_from_temp(temp: float) -> float:
    """Simple inverse relationship between temperature and relative humidity."""
    # At high temp → lower humidity, at low temp → higher humidity
    mid = (TEMP_HIGH + TEMP_LOW) / 2.0
    span = TEMP_HIGH - TEMP_LOW
    base = 50.0 - 30.0 * (temp - mid) / (span / 2.0)
    base = float(np.clip(base, 10.0, 90.0))
    noise = float(np.random.normal(0, 2.0))
    return round(float(np.clip(base + noise, 5.0, 95.0)), 1)


# ── Main generation ────────────────────────────────────────────────────────────

def get_phase_and_setpoint(cycle_phase_norm: float):
    """
    Given normalised position within a cycle (0–1), return
    (phase_name, set_temperature).
    """
    boundaries = {
        "Ramp_Up":   RAMP_UP_FRAC,
        "Soak_High": RAMP_UP_FRAC + SOAK_HIGH_FRAC,
        "Ramp_Down": RAMP_UP_FRAC + SOAK_HIGH_FRAC + RAMP_DOWN_FRAC,
        "Soak_Low":  RAMP_UP_FRAC + SOAK_HIGH_FRAC + RAMP_DOWN_FRAC + SOAK_LOW_FRAC,
    }

    if cycle_phase_norm < boundaries["Ramp_Up"]:
        t = cycle_phase_norm / RAMP_UP_FRAC
        set_temp = TEMP_AMBIENT + cubic_ease(t) * (TEMP_HIGH - TEMP_AMBIENT)
        return "Ramp_Up", set_temp

    elif cycle_phase_norm < boundaries["Soak_High"]:
        return "Soak_High", TEMP_HIGH

    elif cycle_phase_norm < boundaries["Ramp_Down"]:
        t = (cycle_phase_norm - boundaries["Soak_High"]) / RAMP_DOWN_FRAC
        set_temp = TEMP_HIGH + cubic_ease(t) * (TEMP_LOW - TEMP_HIGH)
        return "Ramp_Down", set_temp

    elif cycle_phase_norm < boundaries["Soak_Low"]:
        return "Soak_Low", TEMP_LOW

    else:
        t = (cycle_phase_norm - boundaries["Soak_Low"]) / RAMP_BACK_FRAC
        set_temp = TEMP_LOW + cubic_ease(t) * (TEMP_AMBIENT - TEMP_LOW)
        return "Ramp_Back", set_temp


def generate_data() -> pd.DataFrame:
    np.random.seed(42)  # reproducible output

    cycle_duration_s = CYCLE_HOURS * 3600  # seconds per cycle
    samples_per_cycle = cycle_duration_s // SAMPLE_INTERVAL_S  # 2,880

    rows = []
    start_time = datetime(2025, 1, 1, 0, 0, 0)
    prev_actual = TEMP_AMBIENT  # for exponential smoothing

    for i in range(1, TOTAL_SAMPLES + 1):  # 1-based: first sample at 10 s, last at 168 h
        elapsed_s = i * SAMPLE_INTERVAL_S
        elapsed_hours = elapsed_s / 3600.0

        cycle_number = elapsed_s // cycle_duration_s + 1  # 1-based
        cycle_number = int(min(cycle_number, NUM_CYCLES))

        pos_in_cycle_s = elapsed_s % cycle_duration_s
        cycle_phase_norm = pos_in_cycle_s / cycle_duration_s

        phase, set_temp = get_phase_and_setpoint(cycle_phase_norm)

        # Thermal lag (exponential smoothing toward set point)
        lagged_temp = prev_actual + ALPHA_SMOOTH * (set_temp - prev_actual)

        # Sensor noise
        noise = float(np.random.normal(0, NOISE_STD))
        actual_temp = round(lagged_temp + noise, 2)
        prev_actual = lagged_temp  # smooth without noise for next step

        deviation = round(actual_temp - set_temp, 2)
        humidity = humidity_from_temp(actual_temp)
        timestamp = start_time + timedelta(seconds=elapsed_s)

        rows.append({
            "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Elapsed_Hours": round(elapsed_hours, 6),
            "Cycle_Number": cycle_number,
            "Phase": phase,
            "Set_Temperature": round(set_temp, 2),
            "Actual_Temperature": actual_temp,
            "Deviation": deviation,
            "Humidity_%": humidity,
        })

    df = pd.DataFrame(rows)
    return df


def save_to_excel(df: pd.DataFrame, filename: str = "temperature_cycling_test_data.xlsx"):
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Temperature_Data")

        ws = writer.sheets["Temperature_Data"]

        # Freeze header row
        ws.freeze_panes = "A2"

        # Column widths
        col_widths = {
            "A": 22,  # Timestamp
            "B": 16,  # Elapsed_Hours
            "C": 14,  # Cycle_Number
            "D": 14,  # Phase
            "E": 18,  # Set_Temperature
            "F": 20,  # Actual_Temperature
            "G": 12,  # Deviation
            "H": 14,  # Humidity_%
        }
        for col, width in col_widths.items():
            ws.column_dimensions[col].width = width

    print(f"✓ Saved: {filename}")


def print_summary(df: pd.DataFrame):
    print("\n🔬 Temperature Cycling Test Data Summary")
    print(f"  Total data points  : {len(df):,}")
    print(f"  Sampling interval  : {SAMPLE_INTERVAL_S} seconds")
    print(f"  Total duration     : {TOTAL_HOURS} hours")
    print(f"  Number of cycles   : {df['Cycle_Number'].nunique()} (expected {NUM_CYCLES})")
    print(f"  Cycle_Number range : {df['Cycle_Number'].min()} – {df['Cycle_Number'].max()}")
    print(f"  First Elapsed_Hours: {df['Elapsed_Hours'].iloc[0]}")
    print(f"  Last  Elapsed_Hours: {df['Elapsed_Hours'].iloc[-1]}")
    print(f"  Temp range         : {df['Actual_Temperature'].min():.2f}°C – "
          f"{df['Actual_Temperature'].max():.2f}°C")
    print(f"  Avg deviation      : {df['Deviation'].abs().mean():.4f}°C")
    print(f"  Timestamp interval : "
          f"{(pd.to_datetime(df['Timestamp'].iloc[1]) - pd.to_datetime(df['Timestamp'].iloc[0])).seconds}s")

    # Validate row count
    expected = TOTAL_SAMPLES
    actual = len(df)
    status = "✅" if actual == expected else "❌"
    print(f"\n{status} Row count: {actual:,} (expected {expected:,})")


if __name__ == "__main__":
    print("🔬 Temperature Cycling Test Data Generator")
    print(f"   Sampling interval : {SAMPLE_INTERVAL_S}s")
    print(f"   Total samples     : {TOTAL_SAMPLES:,}")
    print(f"   Cycles            : {NUM_CYCLES}")
    print("   Generating data…")

    df = generate_data()
    print_summary(df)

    output_file = "temperature_cycling_test_data.xlsx"
    print(f"\n   Saving to {output_file}…")
    save_to_excel(df, output_file)
    print("✅ Done!")
