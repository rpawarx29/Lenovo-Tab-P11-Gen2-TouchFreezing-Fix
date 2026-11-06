#
# Himax HX83102J High-Performance Touchscreen Configuration
# Lenovo Tab P11 Gen 2 (TB350XU)
#

# Device Type: explicitly identify as direct touchscreen
touch.deviceType = touchScreen

# Coordinate & Orientation Mapping
touch.orientationAware = 1

# Gesture Mode: spots for multi-touch
touch.gestureMode = spots

# Pressure Calibration: Physical mapping to enable instant touch press detection
touch.pressure.calibration = physical
touch.pressure.scale = 0.001

# Size & Area Calibration: Accurate contact area estimation
touch.size.calibration = area
touch.size.scale = 1.0
touch.size.bias = 0
touch.size.isSummed = 0

# Orientation Calibration
touch.orientation.calibration = none

# Distance & Hover (disable hover to avoid false pre-touch states)
touch.distance.calibration = none

# High-Precision Motion Filter: Level 1 provides zero-lag smoothing
touch.filter.level = 1
