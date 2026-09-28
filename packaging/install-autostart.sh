#!/usr/bin/env bash
# Faz o indicador subir sozinho no login. NAO precisa de root.
#
# Duas formas, e a diferenca importa:
#
#   systemd (padrao)  o processo e supervisionado: se morrer, volta. O journal
#                     guarda o motivo.
#   autostart XDG     dispara e esquece. Se o processo morrer, o icone some e
#                     nada registra o que houve — foi exatamente o que aconteceu
#                     com o indicador que deu origem a este projeto.
set -euo pipefail
MODO="${1:-systemd}"

case "$MODO" in
  systemd)
    mkdir -p ~/.config/systemd/user
    install -m 644 "$(dirname "$0")/clamav-tray.service" ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now clamav-tray.service
    echo "Ativado. Estado: systemctl --user status clamav-tray"
    echo "Desinstalar: systemctl --user disable --now clamav-tray && rm ~/.config/systemd/user/clamav-tray.service"
    ;;
  xdg)
    mkdir -p ~/.config/autostart
    install -m 644 "$(dirname "$0")/clamav-tray.desktop" ~/.config/autostart/
    echo "Ativado via autostart XDG (sem supervisao — prefira o modo systemd)."
    echo "Desinstalar: rm ~/.config/autostart/clamav-tray.desktop"
    ;;
  *) echo "uso: $0 [systemd|xdg]"; exit 1;;
esac
