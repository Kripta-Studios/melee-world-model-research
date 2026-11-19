#!/usr/bin/env bash
# Reanuda los servicios GEX/Discord detenidos durante la investigación.
cd "$(dirname "$0")"
systemctl reset-failed $(cat stopped_services.txt) 2>/dev/null
systemctl start $(cat stopped_services.txt) $(cat stopped_timers.txt)
for u in $(cat stopped_services.txt stopped_timers.txt); do echo "$u $(systemctl is-active $u)"; done
