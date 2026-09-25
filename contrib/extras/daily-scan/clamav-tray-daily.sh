#!/usr/bin/env bash
# Varredura diaria da home. Roda como root via systemd.
#
# Generalizado a partir de um script em uso diario desde 22/09/2026. Os numeros
# nos comentarios sao medidos naquela maquina, nao estimados.
set -uo pipefail

# --- configuracao ---------------------------------------------------------
SCAN_USER="${CLAMAV_TRAY_USER:?defina CLAMAV_TRAY_USER}"
SCAN_DIR="${CLAMAV_TRAY_DIR:-/home/$SCAN_USER}"   # absoluto: sob systemd $HOME vem vazio
QUARANTINE="${CLAMAV_TRAY_QUARANTINE:-/var/quarantine/clamav}"
LOGFILE="${CLAMAV_TRAY_LOG:-/var/log/clamav/scan.log}"
SOCKET="${CLAMAV_TRAY_SOCKET:-}"
[ -n "$SOCKET" ] || SOCKET="$(clamconf -n 2>/dev/null | sed -n 's/^LocalSocket = "\(.*\)"$/\1/p' | head -1)"

RUNLOG="$(mktemp)"; LISTA="$(mktemp)"
trap 'rm -f "$RUNLOG" "$LISTA"' EXIT
mkdir -p "$QUARANTINE" "$(dirname "$LOGFILE")"
chmod 750 "$QUARANTINE"

# Entrega notificacao na sessao grafica. Nunca pode derrubar a unidade.
notify_user() {
    local uid gs_pid disp
    uid="$(id -u "$SCAN_USER" 2>/dev/null)" || return 0
    gs_pid="$(pgrep -u "$SCAN_USER" -x gnome-shell | head -1)"
    # Sem sessao grafica, gs_pid vem vazio e "/proc//environ" nao existe. O
    # 2>/dev/null NAO cobre isso: quem reclama e o redirecionamento, feito pelo
    # shell antes do comando comecar.
    if [ -n "$gs_pid" ] && [ -r "/proc/${gs_pid}/environ" ]; then
        disp="$(tr '\0' '\n' < "/proc/${gs_pid}/environ" | sed -n 's/^DISPLAY=//p' | head -1)"
    fi
    sudo -u "$SCAN_USER" DISPLAY="${disp:-:0}" \
        DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
        notify-send "$1" "$2" >/dev/null 2>&1 || true
}

[ -d "$SCAN_DIR" ] || { echo "ABORTADO: $SCAN_DIR nao existe" >> "$LOGFILE"; exit 1; }
# O daemon e pre-requisito. Falhar aqui e melhor que cair no clamscan em silencio:
# o ponto de usar clamdscan e justamente nao pagar a carga da base a cada execucao.
[ -S "$SOCKET" ] || { echo "ABORTADO: clamd fora do ar ($SOCKET)" >> "$LOGFILE"; exit 1; }

echo "===== $(date) - Iniciando em $SCAN_DIR =====" >> "$LOGFILE"
T0=$SECONDS

# EXCLUSOES. Volume enorme, risco desprezivel: binario de jogo assinado pela loja,
# cache de navegador, pacote gerenciado. O que NAO sai e onde o risco mora —
# Downloads, Documentos, codigo, anexos.
#
# -print0 e depois tr: o --file-list e delimitado por LINHA, entao um nome de
# arquivo que contenha \n vira dois caminhos inexistentes. Medido: um PDF com
# quebra de linha no nome gerava 2 erros por execucao.
find "$SCAN_DIR" \
    \( -path "${SCAN_DIR}/.cache" \
    -o -path "${SCAN_DIR}/.local/share/Trash" \
    -o -path "${SCAN_DIR}/.local/share/Steam" \
    -o -path "${SCAN_DIR}/.local/share/lutris" \
    -o -path "${SCAN_DIR}/.local/share/pnpm" \
    -o -path "${SCAN_DIR}/.local/share/virtualenvs" \
    -o -path "${SCAN_DIR}/.local/share/pipx" \
    -o -path "${SCAN_DIR}/.config/google-chrome" \
    -o -path "${SCAN_DIR}/.mozilla/firefox" \
    -o -name "node_modules" -o -name ".venv" -o -name "venv" \
    -o -name "__pycache__" -o -name ".cache" \
    -o -path "*/.git/objects" \
    \) -prune -o -type f -print0 2>/dev/null | tr '\0' '\n' > "$LISTA"

N_ARQ=$(wc -l < "$LISTA")
echo "arquivos na fila: $N_ARQ" >> "$LOGFILE"

clamdscan --fdpass -i --move="$QUARANTINE" --file-list="$LISTA" > "$RUNLOG" 2>&1
RC=$?
DUR=$(( SECONDS - T0 ))
cat "$RUNLOG" >> "$LOGFILE"
printf '===== %s - Fim (rc=%d) em %dh%02dm, %s arquivos =====\n\n' \
    "$(date)" "$RC" $((DUR/3600)) $(((DUR%3600)/60)) "$N_ARQ" >> "$LOGFILE"

# Publica o resumo da quarentena para o tray poder mostrar (ele roda como usuario
# e nao consegue nem contar dentro de um diretorio 750 de root).
PUB="$(dirname "$0")/../../publish-quarantine-stats.sh"
[ -x "$PUB" ] && "$PUB" "$QUARANTINE" || true

# O VEREDITO VEM DO RESUMO, NAO DO CODIGO DE SAIDA.
# O clamdscan devolve 2 se QUALQUER arquivo nao pode ser aberto, e numa varredura
# de horas sobre um milhao de arquivos e rotina que temporarios sumam no meio.
# Tratar isso como falha faz o servico gritar todo dia — e alarme que sempre toca
# deixa de ser alarme.
INFECTADOS=$(sed -n 's/^Infected files:[[:space:]]*\([0-9]\+\).*/\1/p' "$RUNLOG" | tail -1)
ILEGIVEIS=$(sed -n 's/^Total errors:[[:space:]]*\([0-9]\+\).*/\1/p' "$RUNLOG" | tail -1)

if [ -z "$INFECTADOS" ]; then
    notify_user "ClamAV" "A varredura nao concluiu (rc=$RC). Veja $LOGFILE"
    exit "${RC:-1}"
fi
RESSALVA=""
[ "${ILEGIVEIS:-0}" -gt 0 ] && RESSALVA=" ($ILEGIVEIS ilegivel(is))"
if [ "$INFECTADOS" -gt 0 ]; then
    notify_user "ClamAV" "$INFECTADOS ameaca(s). Veja $QUARANTINE"
else
    notify_user "ClamAV" "Varredura concluida em $((DUR/60)) min. Nenhuma ameaca.$RESSALVA"
fi
exit 0
