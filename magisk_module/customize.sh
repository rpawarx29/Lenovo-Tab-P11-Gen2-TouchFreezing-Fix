ui_print "***************************************************"
ui_print "*  Helio G99 Extreme Overclock & Adaptive Boost   *"
ui_print "*  Lenovo Tab P11 Gen 2 (TB350XU)                 *"
ui_print "***************************************************"
ui_print "- CPU LITTLE Cluster: 1.5 GHz - 2.0 GHz"
ui_print "- CPU BIG Cluster:    1.7 GHz - 2.2 GHz"
ui_print "- GPU Mali-G57:       648 MHz - 1.10 GHz (Unlocked)"
ui_print "- Schedutil Latency:  0us instant ramp-up"
ui_print "- MediaTek fpsgo:     Thermal throttling bypassed"
ui_print "- Display:            120Hz locked (zero stutter)"
ui_print "- Touch Profile:      Himax high-res .idc injected"
ui_print "- Stylus Profile:     Precision Pen 2 anti-jitter IDC"
ui_print "- Adaptive Standby:   Auto-cool on screen sleep"
ui_print "- I/O & VM:           VFS cache 50, Readahead 1024KB"
ui_print "- Installing module service and system overlays..."
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/system" 0 0 0755 0644

if [ -d "/data/system/devices/idc" ]; then
    ui_print "- Injected calibrated IDCs directly to /data/system/devices/idc/..."
    cp -f "$MODPATH/system/usr/idc/"*.idc /data/system/devices/idc/ 2>/dev/null
    chown system:system /data/system/devices/idc/*.idc 2>/dev/null
    chmod 644 /data/system/devices/idc/*.idc 2>/dev/null
fi

ui_print "- Installation Complete!"
