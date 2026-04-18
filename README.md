# High-Low Temperature Cycling Test Data

Automated generator for 168-hour (7-day) high-low temperature cycling test data, suitable for evaluating sensor and component reliability under thermal stress.

## 📊 Data Specifications

| Parameter | Value |
|---|---|
| Total duration | 168 hours (7 days) |
| Sampling interval | 5 minutes |
| Total data points | 2,016 |
| Number of cycles | 21 complete cycles |
| Temperature range | -55°C to +125°C |

## 🔄 Single Cycle Profile (8 hours)

| Phase | Duration | Temperature |
|---|---|---|
| Ramp Down | 30 min | 25°C → -55°C |
| Hold Low | 120 min | -55°C (constant) |
| Ramp Up | 90 min | -55°C → 125°C |
| Hold High | 120 min | 125°C (constant) |
| Ramp to Room | 60 min | 125°C → 25°C |
| Hold Room | 60 min | 25°C (constant) |

## 📁 Repository Files

```
sensor-temperature-data/
├── README.md                          # This file
├── generate_temperature_data.py       # Python data generation script
└── temperature_cycling_test_data.xlsx # Pre-generated Excel data file
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yanliang712/sensor-temperature-data.git
cd sensor-temperature-data

# Install dependencies
pip install pandas openpyxl numpy

# Generate data
python generate_temperature_data.py
```

## 📋 Output Columns

| Column | Description |
|---|---|
| Timestamp | Sample time (YYYY-MM-DD HH:MM:SS) |
| Elapsed_Hours | Hours since test start (0.0833 – 168.0) |
| Cycle_Number | Cycle index (1 – 21) |
| Phase | Current phase name |
| Setpoint_Temp_C | Target temperature (°C) |
| Actual_Temp_C | Simulated sensor reading (°C) |
| Deviation_C | Difference between actual and setpoint |
| Humidity_RH | Relative humidity (%) |

## ✅ Data Validation

- Total rows (including header): **2,017**
- Last `Elapsed_Hours`: **168.0**
- `Cycle_Number` range: **1 – 21**
- Temperature continuously cycles for the entire 168 hours with no flat regions
