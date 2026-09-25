#!/usr/bin/env bash
# Publica um resumo da quarentena para o clamav-tray poder mostra-lo.
#
# POR QUE ISTO EXISTE: a quarentena do sistema e tipicamente `750` dono root, e
# isso esta certo — e malware guardado. Um indicador de bandeja roda como usuario
# e nao consegue nem CONTAR o que ha la dentro. Entao quem tem privilegio publica
# um resumo legivel, e o tray le.
#
# Nao expoe nada sensivel: so quantidade, tamanho somado e datas. Nenhum nome de
# arquivo, nenhum conteudo.
#
# USO (como root, no fim da sua varredura ou num timer):
#   publish-quarantine-stats.sh /var/quarantine/clamav
#
# Sem argumento, tenta os caminhos usuais.
set -uo pipefail

QUARANTINE="${1:-}"
if [ -z "$QUARANTINE" ]; then
    for c in /var/quarantine/clamav /var/lib/clamav/quarantine /var/spool/clamav/quarantine; do
        [ -d "$c" ] && QUARANTINE="$c" && break
    done
fi
[ -n "$QUARANTINE" ] && [ -d "$QUARANTINE" ] || exit 0

OUT_DIR="${CLAMAV_TRAY_STATE:-/var/lib/clamav-tray}"
OUT="$OUT_DIR/quarantine.stats"

# O clamdscan cria uma trava por execucao dentro da quarentena e nao a remove
# quando a varredura e interrompida. Conta-las transformaria o indicador em alarme
# falso — medido: seis travas viraram "6 arquivos" no menu.
mapfile -t ENTRIES < <(find "$QUARANTINE" -maxdepth 1 -type f \
    ! -name '.clamav-quarantine-lock*' -printf '%s\t%T@\n' 2>/dev/null)

COUNT=${#ENTRIES[@]}
BYTES=0
NEWEST=""
OLDEST=""
for row in "${ENTRIES[@]}"; do
    size=${row%%$'\t'*}
    mtime=${row##*$'\t'}
    BYTES=$(( BYTES + size ))
    mtime=${mtime%%.*}
    [ -z "$NEWEST" ] || [ "$mtime" -gt "$NEWEST" ] && NEWEST=$mtime
    [ -z "$OLDEST" ] || [ "$mtime" -lt "$OLDEST" ] && OLDEST=$mtime
done

mkdir -p "$OUT_DIR"
TMP="$(mktemp "$OUT.XXXXXX")" || exit 0
{
    echo "path=$QUARANTINE"
    echo "count=$COUNT"
    echo "bytes=$BYTES"
    [ -n "$NEWEST" ] && echo "newest=$(date -u -d "@$NEWEST" +%Y-%m-%dT%H:%M:%S+00:00)"
    [ -n "$OLDEST" ] && echo "oldest=$(date -u -d "@$OLDEST" +%Y-%m-%dT%H:%M:%S+00:00)"
    echo "checked=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
} > "$TMP"

# Troca ATOMICA: o tray pode estar lendo neste instante, e um arquivo pela metade
# viraria contagem errada em vez de erro de leitura.
chmod 0644 "$TMP"
mv -f "$TMP" "$OUT"
