#!/usr/bin/env bash
# Instala o vigia da pasta Downloads. Leia antes de rodar.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "precisa de root: sudo $0 <usuario> [pasta]"; exit 1; }
TARGET_USER="${1:-${SUDO_USER:-}}"
[ -n "$TARGET_USER" ] || { echo "uso: sudo $0 <usuario> [pasta]"; exit 1; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "usuario '$TARGET_USER' nao existe"; exit 1; }
WATCH="${2:-/home/$TARGET_USER/Downloads}"

command -v inotifywait >/dev/null || {
    echo "falta inotifywait. Instale: apt install inotify-tools (ou o equivalente)"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
U=/etc/systemd/system/clamav-tray-downloads.service
[ -e "$U" ] && { echo "JA EXISTE: $U — nada alterado."; exit 1; }
[ -e /usr/local/bin/clamav-tray-downloads.sh ] && {
    echo "JA EXISTE: /usr/local/bin/clamav-tray-downloads.sh — nada alterado."; exit 1; }

install -m 755 "$HERE/clamav-tray-downloads.sh" /usr/local/bin/
install -m 644 "$HERE/clamav-tray-downloads.service" /etc/systemd/system/
cat > /etc/default/clamav-tray-downloads <<CONF
CLAMAV_TRAY_USER=$TARGET_USER
CLAMAV_TRAY_WATCH=$WATCH
CLAMAV_TRAY_QUARANTINE=/var/quarantine/clamav-downloads
CLAMAV_TRAY_LOG=/var/log/clamav/download-scan.log
CONF
chmod 644 /etc/default/clamav-tray-downloads

systemctl daemon-reload
systemctl enable --now clamav-tray-downloads.service

cat <<MSG

Instalado. Vigiando: $WATCH

  estado:      systemctl status clamav-tray-downloads
  acompanhar:  journalctl -fu clamav-tray-downloads
  ajustar:     /etc/default/clamav-tray-downloads

DESINSTALAR:
  systemctl disable --now clamav-tray-downloads
  rm /etc/systemd/system/clamav-tray-downloads.service
  rm /usr/local/bin/clamav-tray-downloads.sh /etc/default/clamav-tray-downloads
  systemctl daemon-reload
MSG
