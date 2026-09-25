#!/usr/bin/env bash
# Varredura automatica de midia removivel. Leia antes de rodar.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "precisa de root: sudo $0 <usuario>"; exit 1; }
TARGET_USER="${1:-${SUDO_USER:-}}"
[ -n "$TARGET_USER" ] || { echo "uso: sudo $0 <usuario>"; exit 1; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "usuario '$TARGET_USER' nao existe"; exit 1; }
command -v findmnt >/dev/null || { echo "falta findmnt (pacote util-linux)"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for f in /etc/systemd/system/clamav-tray-usb@.service \
         /etc/udev/rules.d/99-clamav-tray-usb.rules \
         /usr/local/bin/clamav-tray-usb.sh; do
    [ -e "$f" ] && { echo "JA EXISTE: $f — nada alterado."; exit 1; }
done

# Aviso honesto antes de mexer no sistema.
cat <<'WARN'
ATENCAO: isto varre TODA midia removivel USB assim que voce a pluga, sem
perguntar. Um HD externo de 2 TB dispara uma varredura longa que voce nao pediu.

Para parar uma em curso:  systemctl stop 'clamav-tray-usb@*'
WARN
read -rp "Continuar? [s/N] " r
[ "$r" = "s" ] || [ "$r" = "S" ] || { echo "cancelado."; exit 0; }

install -m 755 "$HERE/clamav-tray-usb.sh" /usr/local/bin/
install -m 644 "$HERE/clamav-tray-usb@.service" /etc/systemd/system/
install -m 644 "$HERE/99-clamav-tray-usb.rules" /etc/udev/rules.d/
cat > /etc/default/clamav-tray-usb <<CONF
CLAMAV_TRAY_USER=$TARGET_USER
CLAMAV_TRAY_QUARANTINE=/var/quarantine/clamav-usb
CLAMAV_TRAY_LOG=/var/log/clamav/usb-scan.log
CLAMAV_TRAY_MOUNT_WAIT=30
CONF
chmod 644 /etc/default/clamav-tray-usb

systemctl daemon-reload
udevadm control --reload-rules

cat <<MSG

Instalado. Plugue um pendrive para testar.

  ver a unidade:  systemctl list-units 'clamav-tray-usb@*'
  acompanhar:     journalctl -fu 'clamav-tray-usb@*'
  parar:          systemctl stop 'clamav-tray-usb@*'

Ela aparece no clamav-tray enquanto roda, porque e unidade de verdade.

DESINSTALAR:
  rm /etc/udev/rules.d/99-clamav-tray-usb.rules
  rm /etc/systemd/system/clamav-tray-usb@.service
  rm /usr/local/bin/clamav-tray-usb.sh /etc/default/clamav-tray-usb
  systemctl daemon-reload && udevadm control --reload-rules
MSG
