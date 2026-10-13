#!/usr/bin/env bash
# Varredura diaria da home: incremental (so o que mudou) na maioria dos dias,
# completa a cada CLAMAV_TRAY_FULL_EVERY dias. Roda como root via systemd.
#
#   clamav-tray-daily.sh [auto|full|incremental]     (padrao: auto)
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
STATE_DIR="${CLAMAV_TRAY_DAILY_STATE:-/var/lib/clamav-tray-daily}"
FULL_EVERY="${CLAMAV_TRAY_FULL_EVERY:-7}"        # dias entre varreduras completas
MODE="${1:-auto}"                                # auto | full | incremental

RUNLOG="$(mktemp)"; LISTA="$(mktemp)"
mkdir -p "$QUARANTINE" "$(dirname "$LOGFILE")" "$STATE_DIR"
chmod 750 "$QUARANTINE"
# Marco de tempo gravado ANTES do find. So vira "ultima varredura" se esta
# terminar com resumo — ver o fim do arquivo.
NOVO_MARCO="$(mktemp -p "$STATE_DIR")"
trap 'rm -f "$RUNLOG" "$LISTA" "$NOVO_MARCO"' EXIT

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

# MODO. A completa percorre a home inteira (horas, medido: 4h40 sobre 1,1 milhao
# de arquivos); a incremental so o que mudou desde a ultima varredura concluida
# (minutos). A completa continua necessaria: a base de assinaturas muda todo dia,
# e so ela reavalia arquivo antigo contra assinatura nova.
#
# Em `auto` (o padrao do timer) a completa roda quando a ultima tem mais de
# FULL_EVERY dias ou nunca rodou. Por idade e nao por dia da semana: maquina
# desligada no domingo nao perde a semana, a completa so acontece no dia seguinte.
MARCO="$STATE_DIR/last-scan"
MARCO_FULL="$STATE_DIR/last-full"
if [ "$MODE" = auto ]; then
    if [ ! -f "$MARCO" ] || [ ! -f "$MARCO_FULL" ] \
        || [ -n "$(find "$MARCO_FULL" -mtime +"$((FULL_EVERY - 1))" 2>/dev/null)" ]; then
        MODE=full
    else
        MODE=incremental
    fi
fi
case "$MODE" in
    full) FILTRO=() ;;
    incremental)
        [ -f "$MARCO" ] || { echo "ABORTADO: incremental sem varredura anterior ($MARCO)" >> "$LOGFILE"; exit 1; }
        # -cnewer (ctime), NAO -newer (mtime). O mtime e o usuario quem define:
        # `touch -d`, `tar x`, `cp -p`, `wget` e `curl -R` gravam a data de origem,
        # e um arquivo recem-baixado com data de 2019 passaria batido. O ctime so
        # o kernel escreve, e qualquer escrita, chmod ou rename o atualiza.
        FILTRO=(-cnewer "$MARCO") ;;
    *) echo "uso: $0 [auto|full|incremental]" >&2; exit 2 ;;
esac

echo "===== $(date) - Iniciando ($MODE) em $SCAN_DIR =====" >> "$LOGFILE"
[ "$MODE" = incremental ] && echo "alterados desde: $(date -r "$MARCO")" >> "$LOGFILE"
T0=$SECONDS

# EXCLUSOES. Volume enorme, risco desprezivel: binario de jogo assinado pela loja,
# cache de navegador, pacote gerenciado. O que NAO sai e onde o risco mora —
# Downloads, Documentos, codigo, anexos.
#
# -print0 e depois tr: o --file-list e delimitado por LINHA, entao um nome de
# arquivo que contenha \n vira dois caminhos inexistentes. Medido: um PDF com
# quebra de linha no nome gerava 2 erros por execucao.
find "$SCAN_DIR" \
    \( -path "${SCAN_DIR}/.local/share/clamav-tray/quarantine" \
    -o -path "${SCAN_DIR}/.cache" \
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
    \) -prune -o -type f "${FILTRO[@]}" -print0 2>/dev/null | tr '\0' '\n' > "$LISTA"

N_ARQ=$(wc -l < "$LISTA")
echo "arquivos na fila: $N_ARQ" >> "$LOGFILE"

clamdscan --fdpass -i --move="$QUARANTINE" --file-list="$LISTA" > "$RUNLOG" 2>&1
RC=$?
DUR=$(( SECONDS - T0 ))
cat "$RUNLOG" >> "$LOGFILE"
printf '===== %s - Fim %s (rc=%d) em %dh%02dm, %s arquivos =====\n\n' \
    "$(date)" "$MODE" "$RC" $((DUR/3600)) $(((DUR%3600)/60)) "$N_ARQ" >> "$LOGFILE"

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
# Concluiu: o marco do INICIO vira a referencia da proxima incremental. Do inicio,
# nao do fim — o que mudou durante a varredura entra na proxima. Varredura que
# nao concluiu nao chega aqui, e a proxima recomeca do marco anterior.
mv -f "$NOVO_MARCO" "$MARCO"
[ "$MODE" = full ] && cp -p "$MARCO" "$MARCO_FULL"
RESSALVA=""
[ "${ILEGIVEIS:-0}" -gt 0 ] && RESSALVA=" ($ILEGIVEIS ilegivel(is))"
if [ "$INFECTADOS" -gt 0 ]; then
    notify_user "ClamAV" "$INFECTADOS ameaca(s). Veja $QUARANTINE"
else
    notify_user "ClamAV" "Varredura $MODE concluida em $((DUR/60)) min, $N_ARQ arquivos. Nenhuma ameaca.$RESSALVA"
fi
exit 0
