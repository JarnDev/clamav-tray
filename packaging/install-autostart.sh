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
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(dirname "$AQUI")"

# COMO O PROGRAMA SERA EXECUTADO.
#
# Instalado por pipx, existe um `clamav-tray` no PATH. Rodando do codigo-fonte,
# nao existe — e a unidade apontava para ele mesmo assim, entao o servico entrava
# em laco de reinicio com status=203/EXEC e o instalador dizia "Ativado".
#
# Agora resolve antes, e recusa se nao houver forma de executar.
if BIN="$(command -v clamav-tray 2>/dev/null)"; then
    EXEC="$BIN"
    TRABALHO=""
elif [ -f "$RAIZ/clamav_tray/__main__.py" ]; then
    EXEC="$(command -v python3) -m clamav_tray"
    TRABALHO="WorkingDirectory=$RAIZ"
    echo "clamav-tray nao esta no PATH; usando o codigo em $RAIZ"
    echo "(depois de 'pipx install .', rode este script de novo para simplificar a unidade)"
else
    echo "Nao encontrei como executar o clamav-tray."
    echo "Instale com 'pipx install .' na raiz do projeto, ou rode este script de dentro dela."
    exit 1
fi

case "$MODO" in
  systemd)
    mkdir -p ~/.config/systemd/user
    # Escreve a unidade com o ExecStart resolvido, em vez de copiar o modelo.
    sed -e "s|^ExecStart=.*|ExecStart=$EXEC|" \
        -e "s|^\[Service\]$|[Service]\n$TRABALHO|" \
        "$AQUI/clamav-tray.service" | grep -v '^$' > ~/.config/systemd/user/clamav-tray.service
    chmod 644 ~/.config/systemd/user/clamav-tray.service
    systemctl --user daemon-reload
    systemctl --user enable --now clamav-tray.service
    sleep 2
    # CONFERE em vez de afirmar: a versao anterior dizia "Ativado" enquanto o
    # servico falhava em laco.
    if systemctl --user is-active --quiet clamav-tray.service; then
        echo "Ativado e rodando."
    else
        echo "FALHOU ao iniciar:"
        systemctl --user status clamav-tray.service --no-pager | head -8
        exit 1
    fi
    echo "Desinstalar: systemctl --user disable --now clamav-tray && rm ~/.config/systemd/user/clamav-tray.service"
    ;;
  xdg)
    mkdir -p ~/.config/autostart
    sed "s|^Exec=.*|Exec=$EXEC|" "$AQUI/clamav-tray.desktop" > ~/.config/autostart/clamav-tray.desktop
    chmod 644 ~/.config/autostart/clamav-tray.desktop
    echo "Ativado via autostart XDG (sem supervisao — prefira o modo systemd)."
    echo "Desinstalar: rm ~/.config/autostart/clamav-tray.desktop"
    ;;
  *) echo "uso: $0 [systemd|xdg]"; exit 1;;
esac
