#!/system/bin/sh
# Lenovo Tab P11 (2nd Gen) - TB350XU (Helio G99 / MT6789)
# Ultimate Touch & Performance Daemon (v6.1-Ultimate)
# Preserves Native Haptics & User Settings Refresh Rate

while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
done

# 1. Disable Lenovo Background OTA Update Pressure & GPU Window Blur Stalls
settings put global ota_disable_automatic_update 1
pm disable-user --user 0 com.lenovo.ota 2>/dev/null
am force-stop com.lenovo.ota 2>/dev/null
settings put global disable_window_blurs 1

write_if_ne() {
    [ -f "$1" ] || return 0
    read -r CUR < "$1" 2>/dev/null
    [ "$CUR" = "$2" ] || echo "$2" > "$1" 2>/dev/null
}

raise_if_lt() {
    [ -f "$1" ] || return 0
    read -r CUR < "$1" 2>/dev/null
    case "$CUR" in
        ''|*[!0-9]*) echo "$2" > "$1" 2>/dev/null ;;
        *) [ "$CUR" -lt "$2" ] && echo "$2" > "$1" 2>/dev/null ;;
    esac
}

apply_awake_static() {
    write_if_ne /sys/devices/system/cpu/cpufreq/policy0/scaling_governor sugov_ext
    write_if_ne /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq 2000000
    write_if_ne /sys/devices/system/cpu/cpufreq/policy6/scaling_governor sugov_ext
    write_if_ne /sys/devices/system/cpu/cpufreq/policy6/scaling_max_freq 2200000
    echo 50 > /proc/sys/vm/vfs_cache_pressure 2>/dev/null
    echo 60 > /proc/sys/vm/swappiness 2>/dev/null
    echo 20 > /proc/sys/vm/dirty_ratio 2>/dev/null
    echo 10 > /proc/sys/vm/dirty_background_ratio 2>/dev/null
    for q in /sys/block/sd*/queue/read_ahead_kb /sys/block/dm-*/queue/read_ahead_kb; do
        [ -f "$q" ] && echo 1024 > "$q" 2>/dev/null
    done
    write_if_ne /sys/kernel/fpsgo/common/force_onoff 0
    write_if_ne /sys/kernel/fpsgo/minitop/enable 0
    write_if_ne /sys/kernel/fpsgo/fbt/enable_switch_down_throttle 0
    write_if_ne /sys/kernel/fpsgo/fbt/enable_ceiling 0
    write_if_ne /sys/kernel/fpsgo/fstb/adopt_low_fps 0
    write_if_ne /sys/kernel/fpsgo/common/stop_boost 0
    write_if_ne /sys/module/ged/parameters/boost_gpu_enable 1
    write_if_ne /sys/module/ged/parameters/ged_smart_boost 1
    write_if_ne /sys/module/ged/parameters/g_fb_dvfs_threshold 45
    [ -f /proc/game_mode ] && echo 0 > /proc/game_mode 2>/dev/null
}

enforce_awake() {
    # Enforce minimum floors without downgrading active PowerHAL launch bursts
    raise_if_lt /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq 1200000
    raise_if_lt /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq 1400000
    write_if_ne /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/up_rate_limit_us 0
    write_if_ne /sys/devices/system/cpu/cpufreq/policy0/sugov_ext/down_rate_limit_us 30000
    write_if_ne /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/up_rate_limit_us 0
    write_if_ne /sys/devices/system/cpu/cpufreq/policy6/sugov_ext/down_rate_limit_us 30000

    raise_if_lt /sys/module/ged/parameters/gpu_bottom_freq 648000
    write_if_ne /sys/module/ged/parameters/gpu_cust_upbound_freq 1100000
    raise_if_lt /sys/module/ged/parameters/gpu_cust_boost_freq 948000
    raise_if_lt /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/min_freq 648000000
    write_if_ne /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/max_freq 1100000000

    write_if_ne /sys/kernel/fpsgo/common/fpsgo_enable 0
    write_if_ne /sys/kernel/fpsgo/fbt/thrm_enable 0
    write_if_ne /sys/kernel/fpsgo/fbt/boost_ta 1

    write_if_ne /dev/cpuctl/top-app/cpu.uclamp.latency_sensitive 1
}

apply_sleep() {
    echo 500000 > /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq 2>/dev/null
    echo 725000 > /sys/devices/system/cpu/cpufreq/policy6/scaling_min_freq 2>/dev/null
    echo 390000 > /sys/module/ged/parameters/gpu_bottom_freq 2>/dev/null
    echo 390000 > /sys/module/ged/parameters/gpu_cust_boost_freq 2>/dev/null
    echo 390000000 > /sys/devices/platform/soc/13000000.mali/devfreq/13000000.mali/min_freq 2>/dev/null
    echo 1 > /sys/kernel/fpsgo/fbt/thrm_enable 2>/dev/null
    echo 0 > /dev/cpuctl/top-app/cpu.uclamp.latency_sensitive 2>/dev/null
}

is_screen_on() {
    if [ -r /sys/class/leds/lcd-backlight/brightness ]; then
        read -r BL < /sys/class/leds/lcd-backlight/brightness 2>/dev/null
        case "$BL" in
            ''|0) return 1 ;;
            *) return 0 ;;
        esac
    fi
    IS_AWAKE=$(dumpsys power 2>/dev/null | grep -E "mWakefulness=Awake|Display Power: state=ON" | head -n 1)
    [ -n "$IS_AWAKE" ]
}

apply_awake_static
enforce_awake

(
    PREV_STATE="Awake"
    while true; do
        if is_screen_on; then
            if [ "$PREV_STATE" != "Awake" ]; then
                apply_awake_static
                PREV_STATE="Awake"
            fi
            enforce_awake
            sleep 2
        else
            if [ "$PREV_STATE" != "Asleep" ]; then
                apply_sleep
                PREV_STATE="Asleep"
            fi
            sleep 5
        fi
    done
) &
