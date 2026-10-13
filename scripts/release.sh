#!/usr/bin/env bash
# Lanca uma versao: confere, sobe o numero, fecha o CHANGELOG, commit + tag
# assinados, push. A publicacao no PyPI quem faz e o publish.yml, disparado pela
# tag — e ele ainda espera aprovacao manual no ambiente "pypi" do GitHub.
#
#   scripts/release.sh 0.3.0            pergunta antes de gravar e antes do push
#   scripts/release.sh 0.3.0 --dry-run  so confere e mostra o que faria
#   scripts/release.sh 0.3.0 --yes      sem perguntas (nao pula as conferencias)
#
# Por que um script: lancar a mao tem seis passos que precisam concordar entre si
# (versao em dois arquivos, CHANGELOG, tag, push por SSH). Na 0.2.0 dois deles
# sairam errados na primeira tentativa: o numero colidia com uma 0.1.0 ja
# registrada no CHANGELOG, e o push por HTTPS foi recusado.
set -euo pipefail

VERSAO="${1:-}"; shift || true
DRY=0; YES=0
for a in "$@"; do
    case "$a" in
        --dry-run) DRY=1 ;;
        --yes) YES=1 ;;
        *) echo "opcao desconhecida: $a" >&2; exit 2 ;;
    esac
done

cd "$(git rev-parse --show-toplevel)"
falha() { echo "ERRO: $*" >&2; exit 1; }
pergunta() { [ "$YES" = 1 ] && return 0; read -r -p "$1 [s/N] " r; [ "$r" = s ] || [ "$r" = S ]; }

# --- conferencias: nada e gravado antes de todas passarem ---------------------
[[ "$VERSAO" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || falha "uso: $0 X.Y.Z [--dry-run|--yes]"

ATUAL=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)
INIT=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' clamav_tray/__init__.py)
[ "$ATUAL" = "$INIT" ] || falha "pyproject ($ATUAL) e __init__ ($INIT) ja divergem — corrija antes"
# sort -V decide "maior": 0.10.0 > 0.9.0, que comparacao de texto erraria.
[ "$(printf '%s\n%s\n' "$ATUAL" "$VERSAO" | sort -V | tail -1)" = "$VERSAO" ] && [ "$ATUAL" != "$VERSAO" ] \
    || falha "$VERSAO nao e maior que a atual ($ATUAL)"
# O CHANGELOG e o registro: um numero ja escrito la conta como usado, mesmo sem tag.
grep -q "^## \[$VERSAO\]" CHANGELOG.md && falha "CHANGELOG ja tem uma secao [$VERSAO]"
git rev-parse -q --verify "refs/tags/v$VERSAO" >/dev/null && falha "tag v$VERSAO ja existe"

[ "$(git branch --show-current)" = main ] || falha "fora da main"
[ -z "$(git status --porcelain)" ] || falha "arvore com mudancas nao commitadas"
git fetch -q origin main
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
    || falha "main local e origin/main divergem — sincronize antes (o CI precisa ter rodado neste commit)"

# Lancar sem nada em "Nao lancado" publicaria uma versao sem dizer o que mudou.
NOTAS=$(awk '/^## \[Unreleased\]/{f=1;next} /^## \[/{f=0} f' CHANGELOG.md | grep -v '^[[:space:]]*$' || true)
[ -n "$NOTAS" ] || falha "a secao [Unreleased] do CHANGELOG esta vazia"

# O CI do commit atual tem que ter passado: a tag publica exatamente este commit.
ORIGEM=$(git remote get-url origin)
if [[ "$ORIGEM" == *github.com* ]] && command -v gh >/dev/null; then
    CI=$(gh run list --commit "$(git rev-parse HEAD)" --workflow CI --json conclusion --jq '.[0].conclusion' 2>/dev/null || true)
    [ "$CI" = success ] || falha "CI deste commit nao esta verde (estado: ${CI:-sem execucao})"
fi

python3 tests/run.py >/dev/null || falha "testes locais falharam"

# Push por SSH: o token HTTPS costuma nao ter o escopo `workflow`, e o GitHub
# recusa push que toque .github/workflows/. Deriva do origin para nao fixar o dono.
REMOTO="${ORIGEM/#https:\/\/github.com\//git@github.com:}"
[[ "$REMOTO" != git@github.com:* || "$REMOTO" == *.git ]] || REMOTO+=.git
REMOTO="${RELEASE_REMOTE:-$REMOTO}"
DATA=$(date +%F)

echo "versao:   $ATUAL -> $VERSAO ($DATA)"
echo "remoto:   $REMOTO"
echo "notas:"
echo "$NOTAS" | sed 's/^/  /' | head -30
[ "$DRY" = 1 ] && { echo; echo "(dry-run: nada foi gravado)"; exit 0; }
echo
pergunta "Gravar commit e tag v$VERSAO assinados?" || { echo "cancelado, nada gravado"; exit 1; }

# --- gravacao -----------------------------------------------------------------
sed -i "s/^version = \"$ATUAL\"$/version = \"$VERSAO\"/" pyproject.toml
sed -i "s/^__version__ = \"$ATUAL\"$/__version__ = \"$VERSAO\"/" clamav_tray/__init__.py
# "Nao lancado" fica, vazia, em cima da secao nova.
sed -i "0,/^## \[Unreleased\]$/s//## [Unreleased]\n\n## [$VERSAO] — $DATA/" CHANGELOG.md

git add pyproject.toml clamav_tray/__init__.py CHANGELOG.md
git commit -S -q -m "versao $VERSAO"
git tag -s "v$VERSAO" -m "clamav-tray $VERSAO"
echo "commit $(git rev-parse --short HEAD) e tag v$VERSAO gravados (locais)."

if ! pergunta "Enviar main e v$VERSAO para $REMOTO? (dispara a publicacao)"; then
    echo "Nao enviado. Para desfazer: git tag -d v$VERSAO && git reset --hard HEAD~1"
    exit 0
fi
# main primeiro: se ela for recusada, a tag nao sai e nada e publicado.
git push "$REMOTO" main
git push "$REMOTO" "v$VERSAO"
git fetch -q origin

REPO=$(echo "$ORIGEM" | sed -E 's#^(https://github.com/|git@github.com:)##; s#\.git$##')
echo
echo "Enviado. A publicacao espera sua aprovacao no ambiente 'pypi':"
echo "  https://github.com/$REPO/actions/workflows/publish.yml"
echo "Depois: https://pypi.org/project/clamav-tray/$VERSAO/"
