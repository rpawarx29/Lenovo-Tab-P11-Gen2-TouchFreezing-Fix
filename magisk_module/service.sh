#!/system/bin/sh
# Lenovo Tab P11 (2nd Gen) - TB350XU (Helio G99 / MT6789)
# Overclock & Adaptive Performance Daemon + Vibration Elimination + OTA Block + 120Hz Lock

# 1. Disable Lenovo OTA Updates
settings put global ota_disable_automatic_update 1
pm disable-user --user 0 com.lenovo.ota 2>/dev/null
am force-stop com.lenovo.ota 2>/dev/null

# 2. Complete Vibration Elimination (Hardware Driver Unbind + Global Settings)
settings put system haptic_feedback_enabled 0
settings put system vibrate_when_ringing 0
settings put system vibrate_on 0
settings put system notification_vibration_intensity 0
settings put system haptic_feedback_intensity 0
settings put system ring_vibration_intensity 0
settings put system hardware_haptic_feedback_intensity 0
settings put system media_vibration_intensity 0

if [ -d "/sys/bus/platform/drivers/regulator_vibrator" ]; then
    echo "soc:regulator_vibrator" > /sys/bus/platform/drivers/regulator_vibrator/unbind 2>/dev/null
fi

# 3. Lock 120Hz High-Refresh Display (Eliminates 60Hz->120Hz dynamic stutter)
settings put system min_refresh_rate 120.0
settings put system peak_refresh_rate 120.0
settings put global disable_window_blurs 1

# 4. User's Overclock & Adaptive Performance Engine
apply_overclock() {
    # CPU LITTLE Cluster (policy0: CPU0-5)
    echo sugov_ext > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor 2>/dev/null || echo schedutil > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
    echo 1500000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq 2>/dev/null
    echo 2000000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq 2>/dev/null
    if [ -d /sys/devices/system/cpu/cpufreq/policy0/sugov_ext ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/up_rate_limit_us 2>/dev/null
        echo 10000 > /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/down_rate_limit_us 2>/dev/null
    elif [ -d /sys/devices/system/cpu/cpufreq/policy0/schedutil ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy0/schedutil/rate_limit_us 2>/dev/null
    fi

    # CPU BIG Cluster (policy6: CPU6-7)
    echo sugov_ext > /sys/devices/system/cpu/cpufreq/policy6/scaling_governor 2>/dev/null || echo schedutil > /sys/devices/system/cpu/cpufreq/policy6/scaling_governor
    echo 1700000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq 2>/dev/null
    echo 2200000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_max_freq 2>/dev/null
    if [ -d /sys/devices/system/cpu/cpufreq/policy6/sugov_ext ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/up_rate_limit_us 2>/dev/null
        echo 10000 > /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/down_rate_limit_us 2>/dev/null
    elif [ -d /sys/devices/system/cpu/cpufreq/policy6/schedutil ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy6/schedutil/rate_limit_us 2>/dev/null
    fi

    # GPU Overclock (Mali-G57 & GED)
    echo 1100000 > /sys/module/ged/parameters/gpu_cust_upbound_freq 2>/dev/null
    echo 648000 > /sys/module/ged/parameters/gpu_bottom_freq 2>/dev/null
    echo 948000 > /sys/module/ged/parameters/gpu_cust_boost_freq 2>/dev/null
    echo 1 > /sys/module/ged/parameters/boost_gpu_enable 2>/dev/null
    echo 1 > /sys/module/ged/parameters/ged_smart_boost 2>/dev/null
    echo 45 > /sys/module/ged/parameters/g_fb_dvfs_threshold 2>/dev/null

    echo 648000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/min_freq 2>/dev/null
    echo 1100000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/max_freq 2>/dev/null

    # MediaTek fpsgo & Frame Rate Stabilization (Zero Throttling)
    echo 0 > /sys/kernel/fpsgo/common/fpsgo_enable 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/common/force_onoff 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/minitop/enable 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fbt/thrm_enable 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fbt/enable_switch_down_throttle 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fbt/enable_ceiling 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fstb/adopt_low_fps 2>/dev/null
    echo 1 > /sys/kernel/fpsgo/fbt/boost_ta 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/common/stop_boost 2>/dev/null

    # VM & I/O
    echo 50 > /proc/sys/vm/vfs_cache_pressure 2>/dev/null
    echo 60 > /proc/sys/vm/swappiness 2>/dev/null
    echo 20 > /proc/sys/vm/dirty_ratio 2>/dev/null
    echo 10 > /proc/sys/vm/dirty_background_ratio 2>/dev/null

    for q in /sys/block/sd*/queue/read_ahead_kb /sys/block/dm-*/queue/read_ahead_kb; do
        [ -f "$q" ] && echo 1024 > "$q" 2>/dev/null
    done
}

apply_sleep() {
    # Drop to low power when screen is off to preserve battery and keep tablet cool
    echo 500000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq 2>/dev/null
    echo 725000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq 2>/dev/null
    echo 390000 > /sys/module/ged/parameters/gpu_bottom_freq 2>/dev/null
    echo 390000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/min_freq 2>/dev/null
}

# Initial apply immediately
apply_overclock

# Background adaptive daemon loop (Zero overhead power state monitor)
(
    PREV_STATE="Awake"
    while true; do
        sleep 3
        if dumpsys power 2>/dev/null | grep -q "mWakefulness=Awake"; then
            CUR_STATE="Awake"
        else
            CUR_STATE="Sleep"
        fi

        if [ "$CUR_STATE" != "$PREV_STATE" ]; then
            if [ "$CUR_STATE" = "Awake" ]; then
                apply_overclock
            else
                apply_sleep
            fi
            PREV_STATE="$CUR_STATE"
        fi
    done
) </dev/null >/dev/null 2>&1 &

exit 0
