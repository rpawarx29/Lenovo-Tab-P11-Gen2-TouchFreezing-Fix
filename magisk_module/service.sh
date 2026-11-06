#!/system/bin/sh
# Helio G99 Extreme Overclock & Adaptive Performance Daemon

# Wait for full system boot
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 2
done
sleep 3

apply_overclock() {
    # 1. CPU LITTLE Cluster (policy0: CPU0-5)
    echo sugov_ext > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor 2>/dev/null || echo schedutil > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
    echo 1500000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq 2>/dev/null
    echo 2000000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq 2>/dev/null
    if [ -d /sys/devices/system/cpu/cpufreq/policy0/sugov_ext ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/up_rate_limit_us 2>/dev/null
        echo 10000 > /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/down_rate_limit_us 2>/dev/null
    elif [ -d /sys/devices/system/cpu/cpufreq/policy0/schedutil ]; then
        echo 500 > /sys/devices/system/cpu/cpufreq/policy0/schedutil/rate_limit_us 2>/dev/null
    fi

    # 2. CPU BIG Cluster (policy6: CPU6-7)
    echo sugov_ext > /sys/devices/system/cpu/cpufreq/policy6/scaling_governor 2>/dev/null || echo schedutil > /sys/devices/system/cpu/cpufreq/policy6/scaling_governor
    echo 1700000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq 2>/dev/null
    echo 2200000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_max_freq 2>/dev/null
    if [ -d /sys/devices/system/cpu/cpufreq/policy6/sugov_ext ]; then
        echo 0 > /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/up_rate_limit_us 2>/dev/null
        echo 10000 > /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/down_rate_limit_us 2>/dev/null
    elif [ -d /sys/devices/system/cpu/cpufreq/policy6/schedutil ]; then
        echo 500 > /sys/devices/system/cpu/cpufreq/policy6/schedutil/rate_limit_us 2>/dev/null
    fi

    # 3. GPU Overclock (Mali-G57 & GED)
    echo 1100000 > /sys/module/ged/parameters/gpu_cust_upbound_freq 2>/dev/null
    echo 648000 > /sys/module/ged/parameters/gpu_bottom_freq 2>/dev/null
    echo 948000 > /sys/module/ged/parameters/gpu_cust_boost_freq 2>/dev/null
    echo 1 > /sys/module/ged/parameters/boost_gpu_enable 2>/dev/null
    echo 1 > /sys/module/ged/parameters/ged_smart_boost 2>/dev/null
    echo 45 > /sys/module/ged/parameters/g_fb_dvfs_threshold 2>/dev/null

    echo 648000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/min_freq 2>/dev/null
    echo 1100000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/max_freq 2>/dev/null

    # 4. MediaTek fpsgo & Frame Rate Stabilization (No Throttling)
    echo 0 > /sys/kernel/fpsgo/fbt/thrm_enable 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fbt/enable_switch_down_throttle 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fbt/enable_ceiling 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/fstb/adopt_low_fps 2>/dev/null
    echo 1 > /sys/kernel/fpsgo/fbt/boost_ta 2>/dev/null
    echo 0 > /sys/kernel/fpsgo/common/stop_boost 2>/dev/null

    # 5. Lock 120Hz High-Refresh Display (Eliminates 60Hz->120Hz dynamic stutter)
    settings put system min_refresh_rate 120.0 2>/dev/null
    settings put system peak_refresh_rate 120.0 2>/dev/null

    # 6. VM & I/O
    echo 50 > /proc/sys/vm/vfs_cache_pressure 2>/dev/null
    echo 60 > /proc/sys/vm/swappiness 2>/dev/null
    echo 20 > /proc/sys/vm/dirty_ratio 2>/dev/null
    echo 10 > /proc/sys/vm/dirty_background_ratio 2>/dev/null

    for q in /sys/block/sd*/queue/read_ahead_kb; do
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

# Initial apply
apply_overclock

# Adaptive daemon loop using DRM DPMS (Zero overhead)
PREV_DPMS=""
while true; do
    sleep 3
    if [ -f /sys/class/drm/card0-DSI-1/dpms ]; then
        CUR_DPMS="$(cat /sys/class/drm/card0-DSI-1/dpms 2>/dev/null)"
    else
        CUR_DPMS="On"
    fi

    if [ "$CUR_DPMS" != "$PREV_DPMS" ]; then
        if [ "$CUR_DPMS" = "On" ]; then
            apply_overclock
        else
            apply_sleep
        fi
        PREV_DPMS="$CUR_DPMS"
    fi
done &
