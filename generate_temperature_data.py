"""
High-Low Temperature Cycling Test Data Generator
=================================================
Generates 168-hour (7-day) temperature cycling test data for high-precision sensors
and exports it to a formatted Excel file.

Test Profile
------------
- Temperature range : -55°C to 125°C
- Sampling interval : 5 minutes
- Total data points : 2,016 (168 h × 60 min ÷ 5 min)
- Complete cycles   : 3  (each 8 hours / 480 minutes)
- Remaining time    : Ambient-temperature stability test

Single-cycle phases (480 min total)
-------------------------------------
1. Cool-Down         30 min  ambient → -55°C
2. Low-Temp Hold    120 min  -55°C
3. Heat-Up           90 min  -55°C → 125°C
4. High-Temp Hold   120 min  125°C
5. Cool-to-Ambient   60 min  125°C → ambient
6. Ambient Hold      60 min  ambient
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Test parameters
# ---------------------------------------------------------------------------
AMBIENT_TEMP = 25.0          # °C  – room temperature reference
LOW_TEMP = -55.0             # °C  – cold-soak temperature
HIGH_TEMP = 125.0            # °C  – hot-soak temperature
NOISE_SIGMA = 0.8            # °C  – sensor Gaussian noise standard deviation
LAG_ALPHA = 0.95             # exponential-smoothing factor (higher = faster tracking, less lag)

SAMPLE_INTERVAL_MIN = 5      # minutes between samples
TOTAL_HOURS = 168            # total test duration (hours)
NUM_CYCLES = 3               # number of complete thermal cycles
CYCLE_DURATION_MIN = 480     # minutes per cycle (8 hours)

TOTAL_POINTS = TOTAL_HOURS * 60 // SAMPLE_INTERVAL_MIN   # 2,016

# Phase boundary offsets within one cycle (minutes from cycle start)
_PHASE_BOUNDS = [
    ("Cool-Down",        0,   30),    # ambient → -55°C
    ("Low-Temp Hold",   30,  150),    # -55°C soak
    ("Heat-Up",        150,  240),    # -55°C → 125°C
    ("High-Temp Hold", 240,  360),    # 125°C soak
    ("Cool-to-Ambient",360,  420),    # 125°C → ambient
    ("Ambient Hold",   420,  480),    # ambient soak
]

# ---------------------------------------------------------------------------
# Helper: cubic ease-in-out for smooth ramp transitions
# ---------------------------------------------------------------------------

def _cubic_ease(t: float) -> float:
    """Return smoothstep value in [0, 1] for normalised progress t ∈ [0, 1]."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if t < 0.5:
        return 4.0 * t ** 3
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def _ramp(t_min: float, t_start: float, t_end: float,
          temp_start: float, temp_end: float) -> float:
    """Interpolate temperature along a cubic-eased ramp."""
    progress = (t_min - t_start) / (t_end - t_start)
    return temp_start + _cubic_ease(progress) * (temp_end - temp_start)


# ---------------------------------------------------------------------------
# Set-temperature profile for one cycle
# ---------------------------------------------------------------------------

def _cycle_set_temps(points_per_cycle: int):
    """
    Return (set_temps, phases) arrays for one 8-hour cycle.

    Both arrays have length *points_per_cycle* (= 96 for 5-min intervals).
    """
    set_temps = []
    phases = []

    for i in range(points_per_cycle):
        t = i * SAMPLE_INTERVAL_MIN  # elapsed minutes within cycle

        if t < 30:
            temp = _ramp(t, 0, 30, AMBIENT_TEMP, LOW_TEMP)
            phase = "Cool-Down"
        elif t < 150:
            temp = LOW_TEMP
            phase = "Low-Temp Hold"
        elif t < 240:
            temp = _ramp(t, 150, 240, LOW_TEMP, HIGH_TEMP)
            phase = "Heat-Up"
        elif t < 360:
            temp = HIGH_TEMP
            phase = "High-Temp Hold"
        elif t < 420:
            temp = _ramp(t, 360, 420, HIGH_TEMP, AMBIENT_TEMP)
            phase = "Cool-to-Ambient"
        else:
            temp = AMBIENT_TEMP
            phase = "Ambient Hold"

        set_temps.append(round(temp, 4))
        phases.append(phase)

    return set_temps, phases


# ---------------------------------------------------------------------------
# Humidity model
# ---------------------------------------------------------------------------

def _humidity_for_temp(temp: float, rng: np.random.Generator) -> float:
    """Return a physically plausible relative humidity (%) for a given temperature."""
    if temp < -40:
        return float(rng.uniform(10, 20))
    if temp < 0:
        return float(rng.uniform(25, 55))
    if temp > 100:
        return float(rng.uniform(10, 30))
    if temp > 60:
        return float(rng.uniform(20, 50))
    # Normal operating range: 0–60 °C
    return float(rng.uniform(40, 80))


# ---------------------------------------------------------------------------
# Main data-generation routine
# ---------------------------------------------------------------------------

def generate_data(seed: int = 42) -> pd.DataFrame:
    """Generate the complete 2 016-point temperature cycling dataset."""
    rng = np.random.default_rng(seed)

    points_per_cycle = CYCLE_DURATION_MIN // SAMPLE_INTERVAL_MIN  # 96

    # --- Build set-temperature and phase arrays ---
    set_temps: list[float] = []
    phases: list[str] = []
    cycle_nums: list[int] = []

    for cycle_idx in range(NUM_CYCLES):
        cyc_temps, cyc_phases = _cycle_set_temps(points_per_cycle)
        set_temps.extend(cyc_temps)
        phases.extend(cyc_phases)
        cycle_nums.extend([cycle_idx + 1] * points_per_cycle)

    # Remaining points: ambient stability test
    cycling_points = NUM_CYCLES * points_per_cycle
    stability_points = TOTAL_POINTS - cycling_points
    set_temps.extend([AMBIENT_TEMP] * stability_points)
    phases.extend(["Ambient Stability"] * stability_points)
    cycle_nums.extend([0] * stability_points)  # 0 = stability phase (no cycle)

    set_arr = np.array(set_temps, dtype=float)

    # --- Sensor response lag (exponential smoothing) ---
    actual_arr = np.empty_like(set_arr)
    actual_arr[0] = AMBIENT_TEMP
    for i in range(1, len(set_arr)):
        actual_arr[i] = LAG_ALPHA * set_arr[i] + (1.0 - LAG_ALPHA) * actual_arr[i - 1]

    # --- Add Gaussian measurement noise ---
    actual_arr += rng.normal(0.0, NOISE_SIGMA, len(set_arr))

    deviation_arr = actual_arr - set_arr

    # --- Humidity ---
    humidity_arr = np.array(
        [_humidity_for_temp(t, rng) for t in set_arr], dtype=float
    )

    # --- Timestamps ---
    start_dt = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [
        (start_dt + timedelta(minutes=i * SAMPLE_INTERVAL_MIN)).strftime("%Y-%m-%d %H:%M:%S")
        for i in range(TOTAL_POINTS)
    ]
    elapsed_hours = [round(i * SAMPLE_INTERVAL_MIN / 60.0, 4) for i in range(TOTAL_POINTS)]

    df = pd.DataFrame({
        "Timestamp":       timestamps,
        "Elapsed_Hours":   elapsed_hours,
        "Cycle_Number":    cycle_nums,
        "Phase":           phases,
        "Set_Temp_C":      np.round(set_arr, 2),
        "Actual_Temp_C":   np.round(actual_arr, 2),
        "Deviation_C":     np.round(deviation_arr, 2),
        "Humidity_Percent": np.round(humidity_arr, 1),
    })

    return df


# ---------------------------------------------------------------------------
# Excel export with formatting
# ---------------------------------------------------------------------------

FILL_HEADER = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
FONT_HEADER = Font(bold=True, color="FFFFFF")
FILL_LOW    = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
FILL_HIGH   = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")


def save_excel(df: pd.DataFrame, filename: str = "temperature_cycling_test_data.xlsx") -> str:
    """
    Write *df* to *filename* as a formatted Excel workbook.

    Formatting applied:
    - Frozen header row
    - Bold white-on-blue column headers
    - Blue row fill  for Set_Temp_C < -40 °C (low-temperature zone)
    - Orange row fill for Set_Temp_C > 100 °C (high-temperature zone)
    - Auto-fitted column widths
    """
    # Write raw data first (openpyxl engine)
    df.to_excel(filename, index=False, engine="openpyxl")

    wb = load_workbook(filename)
    ws = wb.active

    # Freeze header row
    ws.freeze_panes = "A2"

    # Format header row
    for col_idx in range(1, len(df.columns) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
        cell.alignment = Alignment(horizontal="center")

    # Find the Set_Temp_C column index (1-based)
    set_temp_col_idx = df.columns.get_loc("Set_Temp_C") + 1

    # Apply row colour coding
    for row_idx in range(len(df)):
        excel_row = row_idx + 2  # +1 for 0-index, +1 for header
        set_temp = df.iloc[row_idx]["Set_Temp_C"]

        if set_temp < -40:
            row_fill = FILL_LOW
        elif set_temp > 100:
            row_fill = FILL_HIGH
        else:
            row_fill = None

        if row_fill is not None:
            for col_idx in range(1, len(df.columns) + 1):
                ws.cell(row=excel_row, column=col_idx).fill = row_fill

    # Auto-fit column widths
    for col_idx, col_name in enumerate(df.columns, start=1):
        max_len = max(
            len(str(col_name)),
            int(df[col_name].astype(str).map(len).max()),
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 4

    wb.save(filename)
    return filename


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("🔬 Temperature Cycling Test Data Generator")
    print("=" * 50)

    df = generate_data()
    filename = save_excel(df)

    cycling_mask = df["Cycle_Number"] > 0
    cyc_df = df[cycling_mask]

    print(f"✓ Generated {len(df):,} data points")
    print(f"✓ Cycling data points : {cycling_mask.sum():,}")
    print(f"  Temperature range   : {cyc_df['Actual_Temp_C'].min():.1f}°C "
          f"to {cyc_df['Actual_Temp_C'].max():.1f}°C")
    print(f"  Average deviation   : {df['Deviation_C'].abs().mean():.2f}°C")
    print(f"  Max deviation       : {df['Deviation_C'].abs().max():.2f}°C")
    print(f"  Average humidity    : {df['Humidity_Percent'].mean():.1f}%")
    print(f"✓ File saved: {filename}")


if __name__ == "__main__":
    main()
