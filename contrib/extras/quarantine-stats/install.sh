#!/usr/bin/env bash
# Publica o resumo da quarentena de root, para o tray poder mostra-lo.
#
# So precisa disto se a quarentena do sistema for ilegivel para o seu usuario,
# que e o caso normal (750, dono root) e esta CERTO — e malware guardado.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "precisa de root: sudo $0 [caminho-da-quarentena]"; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUARANTINE="${1:-}"

for u in clamav-tray-stats.service clamav-tray-stats.timer; do
    [ -e "/etc/systemd/system/$u" ] && { echo "JA EXISTE: $u — nada alterado."; exit 1; }
done

install -m 755 "$HERE/../../publish-quarantine-stats.sh" /usr/local/bin/
install -m 644 "$HERE/clamav-tray-stats.service" /etc/systemd/system/
install -m 644 "$HERE/clamav-tray-stats.timer" /etc/systemd/system/
[ -n "$QUARANTINE" ] && printf 'CLAMAV_TRAY_QUARANTINE=%s\n' "$QUARANTINE" > /etc/default/clamav-tray-stats

systemctl daemon-reload
systemctl enable --now clamav-tray-stats.timer
systemctl start clamav-tray-stats.service

echo
echo "Publicado em /var/lib/clamav-tray/quarantine.stats:"
sed 's/^/  /' /var/lib/clamav-tray/quarantine.stats 2>/dev/null || echo "  (vazio — a quarentena existe?)"
cat <<'MSG'

Atualiza a cada 15 min e no boot.

DESINSTALAR:
  systemctl disable --now clamav-tray-stats.timer
  rm /etc/systemd/system/clamav-tray-stats.{service,timer}
  rm /usr/local/bin/publish-quarantine-stats.sh
  rm -f /etc/default/clamav-tray-stats /var/lib/clamav-tray/quarantine.stats
  systemctl daemon-reload
MSG
