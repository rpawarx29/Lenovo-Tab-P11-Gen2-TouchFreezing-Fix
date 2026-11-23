# Calibrated & Stabilized IDC for Himax Precision Pen 2 Stylus
# Lenovo Tab P11 (2nd Gen) - TB350XU (Helio G99 / MT6789)

# 1. Direct Touch Digitizer (Eliminates mouse pointer acceleration curves)
touch.deviceType = touchScreen
touch.orientationAware = 1
touch.gestureMode = spots

# 2. 12-Bit Linear Pressure Calibration (4096 levels: 1/4096 = 0.000244140625)
touch.pressure.calibration = physical
touch.pressure.scale = 0.000244140625

# 3. Distance & Hover Tracking
touch.distance.calibration = scaled
touch.distance.scale = 1.0

# 4. Anti-Jitter Filter (Android InputReader Multi-Point Moving Average Filter)
touch.filter.level = 2
