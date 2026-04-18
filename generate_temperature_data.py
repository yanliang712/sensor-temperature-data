"""
Generate high-low temperature cycling test data.

Cycle sequence (8 hours per cycle, 21 cycles = 168 hours total):
  Phase 1: Ramp DOWN  25°C → -55°C  (0.5 h)
  Phase 2: Soak      -55°C           (2.0 h)
  Phase 3: Ramp UP   -55°C → 125°C  (1.5 h)
  Phase 4: Soak       125°C          (2.0 h)
  Phase 5: Ramp DOWN  125°C → 25°C  (1.0 h)
  Phase 6: Soak        25°C          (1.0 h)

Sampling interval : 10 seconds
Total data points : 60,480  (168 h × 3600 s/h ÷ 10 s/point)
"""

import math
import numpy as np
import pandas as pd

# ── Configuration ────────────────────────────────────────────────────────────

SAMPLE_INTERVAL_S = 10          # seconds between samples
NUM_CYCLES        = 21
T_AMBIENT         = 25.0        # °C  (start / end of every cycle)
T_LOW             = -55.0       # °C
T_HIGH            = 125.0       # °C

# Phase durations in seconds
PHASE_DURATIONS = {
    1: 0.5 * 3600,   # 1 800 s  – ramp down  25 → -55°C
    2: 2.0 * 3600,   # 7 200 s  – soak at -55°C
    3: 1.5 * 3600,   # 5 400 s  – ramp up  -55 → 125°C
    4: 2.0 * 3600,   # 7 200 s  – soak at 125°C
    5: 1.0 * 3600,   # 3 600 s  – ramp down 125 → 25°C
    6: 1.0 * 3600,   # 3 600 s  – soak at 25°C
}

CYCLE_DURATION_S = sum(PHASE_DURATIONS.values())  # 28 800 s = 8 h
TOTAL_DURATION_S = NUM_CYCLES * CYCLE_DURATION_S  # 604 800 s = 168 h

# ── Helpers ──────────────────────────────────────────────────────────────────

def cosine_ramp(t_start: float, t_end: float, fraction: float) -> float:
    """Smooth (cosine-eased) interpolation between two temperatures.

    fraction = 0 → t_start,  fraction = 1 → t_end
    """
    ease = (1.0 - math.cos(math.pi * fraction)) / 2.0
    return t_start + (t_end - t_start) * ease


def temperature_at(t_in_cycle: float) -> tuple[float, int]:
    """Return (temperature, phase_number) for a time offset within one cycle.

    t_in_cycle is the elapsed seconds since the start of the cycle
    (0 ≤ t_in_cycle < CYCLE_DURATION_S).
    """
    cumulative = 0.0
    for phase, duration in PHASE_DURATIONS.items():
        if t_in_cycle < cumulative + duration:
            frac = (t_in_cycle - cumulative) / duration
            frac = max(0.0, min(1.0, frac))   # clamp for float safety

            if phase == 1:   # ramp down  25 → -55
                temp = cosine_ramp(T_AMBIENT, T_LOW, frac)
            elif phase == 2: # soak -55
                temp = T_LOW
            elif phase == 3: # ramp up  -55 → 125
                temp = cosine_ramp(T_LOW, T_HIGH, frac)
            elif phase == 4: # soak 125
                temp = T_HIGH
            elif phase == 5: # ramp down  125 → 25
                temp = cosine_ramp(T_HIGH, T_AMBIENT, frac)
            else:            # phase 6: soak 25
                temp = T_AMBIENT

            return temp, phase
        cumulative += duration

    # Should never reach here; return ambient as fallback
    return T_AMBIENT, 6


# ── Data generation ──────────────────────────────────────────────────────────

def generate_data() -> pd.DataFrame:
    total_points = int(TOTAL_DURATION_S // SAMPLE_INTERVAL_S)  # 60 480

    # Timestamps run from SAMPLE_INTERVAL_S to TOTAL_DURATION_S inclusive so
    # that the last row sits exactly at 168.0 h while keeping exactly 60,480
    # rows (one per 10-second interval).
    timestamps_s  = np.arange(1, total_points + 1, dtype=np.int64) * SAMPLE_INTERVAL_S
    elapsed_hours = timestamps_s / 3600.0

    temperatures = []
    cycle_numbers = []
    phase_numbers = []

    for ts in timestamps_s:
        # Subtract one interval so the sample taken at the exact cycle
        # boundary (e.g. ts == CYCLE_DURATION_S) stays in the current cycle
        # rather than rolling over to the next one.
        cycle_idx   = (ts - SAMPLE_INTERVAL_S) // CYCLE_DURATION_S   # 0-based
        cycle_num   = int(cycle_idx) + 1
        t_in_cycle  = ts - cycle_idx * CYCLE_DURATION_S              # offset in current cycle

        temp, phase = temperature_at(float(t_in_cycle))

        temperatures.append(round(temp, 4))
        cycle_numbers.append(cycle_num)
        phase_numbers.append(phase)

    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0, 0.05, total_points)

    df = pd.DataFrame({
        "Timestamp_s":    timestamps_s,
        "Elapsed_Hours":  np.round(elapsed_hours, 6),
        "Temperature_C":  np.round(np.array(temperatures) + noise, 4),
        "Cycle_Number":   cycle_numbers,
        "Phase_Number":   phase_numbers,
    })

    return df


# ── Excel export ─────────────────────────────────────────────────────────────

def export_to_excel(df: pd.DataFrame, path: str = "temperature_cycling_test_data.xlsx") -> None:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Temperature Data"

    # Header row
    headers = ["Timestamp_s", "Elapsed_Hours", "Temperature_C", "Cycle_Number", "Phase_Number"]
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Data rows (write in chunks for memory efficiency)
    CHUNK = 5000
    rows = df.values.tolist()
    for i in range(0, len(rows), CHUNK):
        for row_offset, row in enumerate(rows[i:i + CHUNK]):
            ws.append(row)

    # Column widths
    widths = [14, 14, 16, 14, 14]
    for col, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ── Summary sheet ──────────────────────────────────────────────────────
    ws_sum = wb.create_sheet("Summary")
    summary = [
        ("Parameter",          "Value"),
        ("Total Cycles",       NUM_CYCLES),
        ("Total Duration (h)", NUM_CYCLES * 8),
        ("Sampling Interval",  f"{SAMPLE_INTERVAL_S} s"),
        ("Total Data Points",  len(df)),
        ("T_Low (°C)",         T_LOW),
        ("T_High (°C)",        T_HIGH),
        ("T_Ambient (°C)",     T_AMBIENT),
        ("Phase 1 Duration",   "0.5 h  – Ramp DOWN  25 → -55°C"),
        ("Phase 2 Duration",   "2.0 h  – Soak at -55°C"),
        ("Phase 3 Duration",   "1.5 h  – Ramp UP  -55 → 125°C"),
        ("Phase 4 Duration",   "2.0 h  – Soak at 125°C"),
        ("Phase 5 Duration",   "1.0 h  – Ramp DOWN 125 → 25°C"),
        ("Phase 6 Duration",   "1.0 h  – Soak at 25°C"),
    ]
    for row in summary:
        ws_sum.append(list(row))
    ws_sum.column_dimensions["A"].width = 24
    ws_sum.column_dimensions["B"].width = 38
    ws_sum["A1"].font = Font(bold=True)
    ws_sum["B1"].font = Font(bold=True)

    # ── Chart sheet (first 3 cycles for readability) ───────────────────────
    ws_chart = wb.create_sheet("Chart")

    # Downsample: every 60th point (i.e. every 10 min) for the chart
    chart_step = 60
    chart_rows = [["Elapsed_Hours", "Temperature_C"]]
    for i in range(0, len(df), chart_step):
        chart_rows.append([df["Elapsed_Hours"].iloc[i], df["Temperature_C"].iloc[i]])

    for row in chart_rows:
        ws_chart.append(row)

    n_chart = len(chart_rows)
    chart = LineChart()
    chart.title = "Temperature Cycling (21 cycles, 168 h)"
    chart.style = 10
    chart.y_axis.title = "Temperature (°C)"
    chart.x_axis.title = "Elapsed Time (h)"
    chart.height = 15
    chart.width  = 30

    data_ref = Reference(ws_chart, min_col=2, min_row=1, max_row=n_chart)
    chart.add_data(data_ref, titles_from_data=True)

    cats_ref = Reference(ws_chart, min_col=1, min_row=2, max_row=n_chart)
    chart.set_categories(cats_ref)
    chart.series[0].graphicalProperties.line.solidFill = "2E75B6"
    # Line width in EMU (English Metric Units); 12,700 EMU = 1 pt; 8,000 ≈ 0.63 pt
    chart.series[0].graphicalProperties.line.width = 8000

    ws_chart.add_chart(chart, "D2")

    wb.save(path)
    print(f"Saved: {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating temperature cycling data …")
    df = generate_data()

    print(f"  Total rows     : {len(df):,}")
    print(f"  First row      : t={df['Timestamp_s'].iloc[0]} s, "
          f"T={df['Temperature_C'].iloc[0]:.2f}°C, "
          f"cycle={df['Cycle_Number'].iloc[0]}, phase={df['Phase_Number'].iloc[0]}")
    print(f"  Last row       : t={df['Timestamp_s'].iloc[-1]} s  "
          f"({df['Elapsed_Hours'].iloc[-1]:.4f} h), "
          f"T={df['Temperature_C'].iloc[-1]:.2f}°C, "
          f"cycle={df['Cycle_Number'].iloc[-1]}, phase={df['Phase_Number'].iloc[-1]}")

    # Quick sanity: first phase should be cooling (T < 25°C)
    mid_phase1 = df[df["Phase_Number"] == 1]["Temperature_C"]
    assert mid_phase1.mean() < T_AMBIENT, "Phase 1 must be cooling, not heating!"
    print("  Phase-1 check  : PASS (cooling)")

    export_to_excel(df)
