#!/usr/bin/env bash
# Instala a varredura diaria. Leia antes de rodar — e o que este arquivo pede.
#
# NAO SOBRESCREVE NADA: se ja existir unidade com estes nomes, ele para e diz.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "precisa de root: sudo $0 <usuario>"; exit 1; }
TARGET_USER="${1:-${SUDO_USER:-}}"
[ -n "$TARGET_USER" ] || { echo "uso: sudo $0 <usuario>"; exit 1; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "usuario '$TARGET_USER' nao existe"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNITS=/etc/systemd/system

for u in clamav-tray-daily.service clamav-tray-daily.timer; do
    if [ -e "$UNITS/$u" ]; then
        echo "JA EXISTE: $UNITS/$u"
        echo "Nada foi alterado. Remova ou renomeie antes de instalar."
        exit 1
    fi
done
if [ -e /usr/local/bin/clamav-tray-daily.sh ]; then
    echo "JA EXISTE: /usr/local/bin/clamav-tray-daily.sh — nada alterado."; exit 1
fi

install -m 755 "$HERE/clamav-tray-daily.sh" /usr/local/bin/clamav-tray-daily.sh
install -m 644 "$HERE/clamav-tray-daily.service" "$UNITS/"
install -m 644 "$HERE/clamav-tray-daily.timer" "$UNITS/"

cat > /etc/default/clamav-tray-daily <<CONF
# Configuracao da varredura diaria do clamav-tray.
CLAMAV_TRAY_USER=$TARGET_USER
CLAMAV_TRAY_DIR=/home/$TARGET_USER
CLAMAV_TRAY_QUARANTINE=/var/quarantine/clamav
CLAMAV_TRAY_LOG=/var/log/clamav/scan.log
CONF
chmod 644 /etc/default/clamav-tray-daily

systemctl daemon-reload
systemctl enable --now clamav-tray-daily.timer

cat <<MSG

Instalado. A varredura roda as 03:00 (com ate 15 min de atraso aleatorio).

  ver o agendamento:   systemctl list-timers clamav-tray-daily.timer
  rodar agora:         systemctl start clamav-tray-daily.service
  acompanhar:          journalctl -fu clamav-tray-daily.service
  ajustar:             /etc/default/clamav-tray-daily

DESINSTALAR:
  systemctl disable --now clamav-tray-daily.timer
  rm /etc/systemd/system/clamav-tray-daily.{service,timer}
  rm /usr/local/bin/clamav-tray-daily.sh /etc/default/clamav-tray-daily
  systemctl daemon-reload

A quarentena em /var/quarantine/clamav NAO e removida pelo desinstalador — ela
guarda o que foi isolado, e apagar isso e decisao sua.
MSG
