#!/usr/bin/env bash
# Vigia uma pasta e varre cada arquivo novo. Roda como root via systemd.
#
# O ganho de usar o daemon aqui e proporcionalmente MAIOR que na varredura
# diaria: cada download disparava uma carga completa da base. Medido em 20
# arquivos na maquina de origem:
#   clamscan   11,56 s  |  992 MB de RAM   (carrega 3,6 mi de assinaturas)
#   clamdscan   0,01 s  |  8,8 MB de RAM   (usa o clamd que ja esta no ar)
# Baixar cinco arquivos seguidos custava cinco cargas de 1 GB.
set -uo pipefail

SCAN_USER="${CLAMAV_TRAY_USER:?defina CLAMAV_TRAY_USER}"
WATCH_DIR="${CLAMAV_TRAY_WATCH:-/home/$SCAN_USER/Downloads}"
QUARANTINE="${CLAMAV_TRAY_QUARANTINE:-/var/quarantine/clamav-downloads}"
LOGFILE="${CLAMAV_TRAY_LOG:-/var/log/clamav/download-scan.log}"

mkdir -p "$QUARANTINE" "$(dirname "$LOGFILE")" 
chmod 750 "$QUARANTINE"
[ -d "$WATCH_DIR" ] || { echo "$WATCH_DIR nao existe"; exit 1; }

notify_user() {
    local uid gs_pid disp
    uid="$(id -u "$SCAN_USER" 2>/dev/null)" || return 0
    gs_pid="$(pgrep -u "$SCAN_USER" -x gnome-shell | head -1)"
    if [ -n "$gs_pid" ] && [ -r "/proc/${gs_pid}/environ" ]; then
        disp="$(tr '\0' '\n' < "/proc/${gs_pid}/environ" | sed -n 's/^DISPLAY=//p' | head -1)"
    fi
    sudo -u "$SCAN_USER" DISPLAY="${disp:-:0}" \
        DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
        notify-send -u critical "$1" "$2" >/dev/null 2>&1 || true
}

echo "===== $(date) - vigiando $WATCH_DIR =====" >> "$LOGFILE"

# close_write cobre o arquivo TERMINADO de escrever; moved_to cobre o que o
# navegador renomeia do .part/.crdownload para o nome final. Varrer em create
# pegaria o arquivo pela metade.
inotifywait -m -q -e close_write -e moved_to --format '%w%f' "$WATCH_DIR" |
while read -r file; do
    [ -f "$file" ] || continue
    RUNLOG="$(mktemp)"
    clamdscan --fdpass -i --move="$QUARANTINE" "$file" > "$RUNLOG" 2>&1
    # grep so nesta execucao. Ler o log ACUMULADO faria todo arquivo seguinte ser
    # reportado como infectado depois da primeira ameaca da vida.
    if grep -q "FOUND" "$RUNLOG"; then
        notify_user "ClamAV" "Ameaca em $(basename "$file") — movido para a quarentena"
        cat "$RUNLOG" >> "$LOGFILE"
    fi
    rm -f "$RUNLOG"
done
