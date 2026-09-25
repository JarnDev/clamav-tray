#!/usr/bin/env bash
# Varredura de midia removivel. Recebe o NOME DE KERNEL da particao (ex.: sdc1),
# nao um caminho — quem resolve o ponto de montagem e este script.
#
# POR QUE ISSO IMPORTA: o udev dispara no evento `add` da particao, que acontece
# ANTES de o automount terminar. Quem espera receber um diretorio pronto recebe
# "sdc1" e aborta. Aqui esperamos a montagem aparecer.
set -uo pipefail

KERNEL="${1:-}"
SCAN_USER="${CLAMAV_TRAY_USER:?defina CLAMAV_TRAY_USER}"
QUARANTINE="${CLAMAV_TRAY_QUARANTINE:-/var/quarantine/clamav-usb}"
LOGFILE="${CLAMAV_TRAY_LOG:-/var/log/clamav/usb-scan.log}"
WAIT_SECS="${CLAMAV_TRAY_MOUNT_WAIT:-30}"
SOCKET="${CLAMAV_TRAY_SOCKET:-}"
[ -n "$SOCKET" ] || SOCKET="$(clamconf -n 2>/dev/null | sed -n 's/^LocalSocket = "\(.*\)"$/\1/p' | head -1)"

RUNLOG="$(mktemp)"; trap 'rm -f "$RUNLOG"' EXIT
mkdir -p "$QUARANTINE" "$(dirname "$LOGFILE")"
chmod 750 "$QUARANTINE"

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

[ -n "$KERNEL" ] || { echo "$(date) ABORTADO: sem nome de dispositivo" >> "$LOGFILE"; exit 1; }

# Espera o automount. findmnt resolve /dev/sdc1 -> /media/user/LABEL.
MOUNTPOINT=""
for _ in $(seq "$WAIT_SECS"); do
    MOUNTPOINT="$(findmnt -n -o TARGET --source "/dev/$KERNEL" 2>/dev/null | head -1)"
    [ -n "$MOUNTPOINT" ] && break
    sleep 1
done
if [ -z "$MOUNTPOINT" ] || [ ! -d "$MOUNTPOINT" ]; then
    echo "$(date) - /dev/$KERNEL nao montou em ${WAIT_SECS}s; nada a varrer" >> "$LOGFILE"
    exit 0   # nao e falha: midia pode ser particao de sistema, swap, ou o usuario nao abriu
fi

echo "===== $(date) - varrendo $MOUNTPOINT (/dev/$KERNEL) =====" >> "$LOGFILE"
T0=$SECONDS

# --multiscan usa as threads do clamd. Aqui NAO ha exclusao a aplicar, entao da
# para varrer o diretorio direto, sem --file-list, e aproveitar o paralelismo —
# diferente da varredura da home, onde a lista existe por causa das exclusoes.
clamdscan --fdpass --multiscan -i --move="$QUARANTINE" "$MOUNTPOINT" > "$RUNLOG" 2>&1
DUR=$(( SECONDS - T0 ))
cat "$RUNLOG" >> "$LOGFILE"

# grep so NESTA execucao. Lendo o log acumulado, todo pendrive seguinte seria
# reportado como infectado depois da primeira ameaca da vida.
INFECTADOS=$(sed -n 's/^Infected files:[[:space:]]*\([0-9]\+\).*/\1/p' "$RUNLOG" | tail -1)
if [ "${INFECTADOS:-0}" -gt 0 ]; then
    notify_user "ClamAV" "$INFECTADOS ameaca(s) em $(basename "$MOUNTPOINT") — isoladas"
else
    notify_user "ClamAV" "$(basename "$MOUNTPOINT") varrido em ${DUR}s. Nenhuma ameaca."
fi
printf '===== %s - fim em %ds =====\n\n' "$(date)" "$DUR" >> "$LOGFILE"
exit 0
