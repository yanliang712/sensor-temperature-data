# High-Low Temperature Cycling Test Data

高精度传感器高低温循环测试数据生成系统

## 项目概述

本项目为高精度传感器生成 **168小时（7天）** 的高低温循环测试数据，模拟真实的温度循环测试工况，并将数据导出为格式化的 Excel 文件。

## 测试参数

| 参数 | 数值 |
|------|------|
| 温度范围 | -55°C ～ +125°C |
| 采样间隔 | 5 分钟 |
| 总采样点数 | 2,016 个 |
| 总测试时长 | 168 小时（7天） |
| 循环次数 | 3 个完整循环 |
| 单循环时长 | 8 小时（480 分钟） |

## 单个循环温度阶段

| 阶段 | 持续时间 | 温度变化 |
|------|----------|----------|
| Cool-Down（降温） | 30 分钟 | 常温 → -55°C |
| Low-Temp Hold（低温保温） | 120 分钟 | -55°C 恒温 |
| Heat-Up（升温） | 90 分钟 | -55°C → +125°C |
| High-Temp Hold（高温保温） | 120 分钟 | +125°C 恒温 |
| Cool-to-Ambient（降至常温） | 60 分钟 | +125°C → 常温 |
| Ambient Hold（常温保温） | 60 分钟 | 常温恒温 |

3 个循环（24小时）结束后，剩余 144 小时为 `Ambient Stability`（常温稳定性测试）。

## 数据真实性模型

- **平滑曲线**：升降温使用立方缓动函数（cubic ease-in-out），避免阶跃变化
- **响应滞后**：指数平滑模型（α = 0.95），模拟传感器热响应延迟
- **测量噪声**：高斯分布（σ = 0.8°C），模拟真实测量误差
- **相对湿度**：根据温度动态计算（低温区偏低，常温区偏高）
- **温度偏差**：最大偏差约 ±2°C，符合高精度传感器规范

## Excel 输出列说明

| 列名 | 说明 |
|------|------|
| `Timestamp` | 时间戳（YYYY-MM-DD HH:MM:SS） |
| `Elapsed_Hours` | 累计小时数 |
| `Cycle_Number` | 循环编号（1-3；0 = 稳定性阶段） |
| `Phase` | 测试阶段名称 |
| `Set_Temp_C` | 设定温度（°C） |
| `Actual_Temp_C` | 实际温度（°C，含噪声和响应滞后） |
| `Deviation_C` | 温度偏差 = 实际 − 设定（°C） |
| `Humidity_Percent` | 相对湿度（%） |

## Excel 格式特性

- 首行表头冻结（方便滚动浏览）
- 表头：深蓝底色 + 白色粗体字
- **蓝色**行：低温区（设定温度 < -40°C）
- **橙色**行：高温区（设定温度 > +100°C）
- 自动调整列宽

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yanliang712/sensor-temperature-data.git
cd sensor-temperature-data

# 2. 安装依赖
pip install pandas openpyxl numpy

# 3. 生成数据
python generate_temperature_data.py
```

运行后输出示例：

```
🔬 Temperature Cycling Test Data Generator
==================================================
✓ Generated 2,016 data points
✓ Cycling data points : 288
  Temperature range   : -56.6°C to 127.3°C
  Average deviation   : 0.65°C
  Max deviation       : 2.92°C
  Average humidity    : 55.4%
✓ File saved: temperature_cycling_test_data.xlsx
```

## 文件结构

```
sensor-temperature-data/
├── README.md                          # 项目文档
├── generate_temperature_data.py       # 数据生成脚本
└── temperature_cycling_test_data.xlsx # 生成的 Excel 数据文件（2,016 行）
```

## 依赖

| 包 | 用途 |
|----|------|
| `numpy` | 数值计算与随机噪声生成 |
| `pandas` | 数据组织与 Excel 写入 |
| `openpyxl` | Excel 格式化（颜色、冻结行、列宽） |
