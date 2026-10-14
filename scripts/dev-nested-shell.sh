#!/usr/bin/env bash
# Abre um GNOME Shell ANINHADO (numa janela) com a extensao do repositorio
# carregada. E onde a extensao e desenvolvida: bug nela derruba so esta janela,
# nunca a barra da sessao real.
#
#   scripts/dev-nested-shell.sh            abre e fica ate fechar a janela
#   scripts/dev-nested-shell.sh 20         fecha sozinho depois de 20 s (testes)
#   CLAMAV_TRAY_DEV_DARK=1 ...             tema escuro (o padrao e o claro)
#   CLAMAV_TRAY_COMMAND='' ...             simula clamav-tray ausente (o padrao e
#                                          o do repositorio, para o --dump)
#   scripts/dev-nested-shell.sh ciclo      sobe, desliga e religa a extensao 3x,
#                                          e fecha: prova que disable() limpa tudo
#
# ISOLAMENTO, que e o ponto deste script: sem ele, o shell aninhado usaria o
# mesmo dconf e a mesma pasta de extensoes da sessao real, e ativar a extensao
# aqui ativaria la tambem. Por isso: barramento D-Bus proprio (dbus-run-session,
# logo um dconf-service proprio) e XDG_CONFIG_HOME/XDG_DATA_HOME descartaveis.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
UUID="clamav-tray@jarndev.github.io"
SEGUNDOS="${1:-}"
DEV="${CLAMAV_TRAY_DEV_DIR:-${XDG_RUNTIME_DIR:-/tmp}/clamav-tray-dev}"

rm -rf "$DEV"; mkdir -p "$DEV/config" "$DEV/data/gnome-shell/extensions" "$DEV/cache"
ln -s "$RAIZ/gnome-extension/$UUID" "$DEV/data/gnome-shell/extensions/$UUID"

export XDG_CONFIG_HOME="$DEV/config" XDG_DATA_HOME="$DEV/data" XDG_CACHE_HOME="$DEV/cache"
# Sem state.json, a extensao roda `clamav-tray --dump --json`: aqui, o do
# repositorio, e nao uma versao instalada que nao tem os campos novos.
export CLAMAV_TRAY_COMMAND="${CLAMAV_TRAY_COMMAND-env PYTHONPATH=$RAIZ python3 -m clamav_tray}"
export MUTTER_DEBUG_DUMMY_MODE_SPECS="${CLAMAV_TRAY_DEV_SIZE:-1280x800}"

ESQUEMA=default; [ -n "${CLAMAV_TRAY_DEV_DARK:-}" ] && ESQUEMA=prefer-dark
PREPARO="gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell enabled-extensions \"['$UUID']\"
gsettings set org.gnome.shell welcome-dialog-last-shown-version '999'
gsettings set org.gnome.desktop.interface color-scheme $ESQUEMA"

if [ "$SEGUNDOS" = ciclo ]; then
    # gnome-extensions fala com o shell pelo barramento DESTA sessao isolada.
    INTERNO="$PREPARO
gnome-shell --nested --wayland & SHELL_PID=\$!
sleep 8
for i in 1 2 3; do
    gnome-extensions disable $UUID; sleep 1
    gnome-extensions enable $UUID; sleep 1
done
gnome-extensions info $UUID | grep -E 'State|Estado'
kill -TERM \$SHELL_PID; wait \$SHELL_PID"
else
    INTERNO="$PREPARO
exec ${SEGUNDOS:+timeout --signal=TERM --kill-after=5 $SEGUNDOS} gnome-shell --nested --wayland"
fi
exec dbus-run-session -- bash -c "$INTERNO"
