ui_print "------------------------------------------------------"
ui_print " Lenovo Tab P11 Gen 2 - S231018 Touch & Perf Fix v2.0 "
ui_print "------------------------------------------------------"
ui_print "- SF Touch Timer:   2000ms (prevents 120->60Hz drop while typing)"
ui_print "- Touch IDCs:       himax-touchscreen + himax-stylus"
ui_print "- CPU Clusters:     1.2-2.0 GHz / 1.4-2.2 GHz (awake floor)"
ui_print "- Sugov Hold Time:  up=0us / down=30000us"
ui_print "- GPU Mali-G57:     648 MHz - 1.10 GHz (awake floor)"
ui_print "- PowerHAL Guard:   Restores drifted awake floors every 2s"
ui_print "- Sleep Profile:    Reverts to 500/725/390 MHz on screen off"
ui_print "- Native Defaults:  Settings RR (60/Auto/120Hz) & haptics preserved"

# Remove older module IDs if upgrading
for OLD_ID in helio_g99_oc tb350xu_master_touch_fix; do
    if [ -d "/data/adb/modules/$OLD_ID" ]; then
        ui_print "- Scheduling removal of legacy module: $OLD_ID"
        touch "/data/adb/modules/$OLD_ID/remove"
        touch "/data/adb/modules/$OLD_ID/disable"
    fi
done

set_perm "$MODPATH/service.sh" 0 0 0755
set_perm_recursive "$MODPATH/system" 0 0 0755 0644
ui_print "- Done. Reboot to apply all changes."
