#!/usr/bin/env bash
# Faz o indicador subir sozinho no login. NAO precisa de root.
#
#   ./packaging/install-autostart.sh          servico de usuario (supervisionado)
#   ./packaging/install-autostart.sh xdg      autostart XDG (sem supervisao)
#
# Desde a 0.3 a logica mora no proprio programa (clamav_tray/autostart.py), para
# quem instalou pelo PyPI nao precisar deste repositorio:
#
#   clamav-tray --show-autostart       mostra o que seria gravado, sem gravar
#   clamav-tray --install-autostart    mostra, pergunta, grava e confere
#
# Este script so encaminha, com os mesmos argumentos de antes. Funciona tambem
# antes de `pipx install`: sem clamav-tray no PATH, roda o codigo deste diretorio.
set -euo pipefail
MODO="${1:-systemd}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

case "$MODO" in
    systemd) ARGS=(--install-autostart) ;;
    xdg)     ARGS=(--install-autostart --xdg) ;;
    *) echo "uso: $0 [systemd|xdg]"; exit 1 ;;
esac

if command -v clamav-tray >/dev/null 2>&1; then
    exec clamav-tray "${ARGS[@]}"
fi
cd "$RAIZ"
exec python3 -m clamav_tray "${ARGS[@]}"
