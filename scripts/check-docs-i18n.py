#!/usr/bin/env python3
"""Confere que a documentacao em ingles e em portugues andam juntas.

    python3 scripts/check-docs-i18n.py

Cada X.md (ingles, o padrao) precisa de um X.pt-BR.md ao lado, e vice-versa —
exceto o CHANGELOG, que e so em ingles por decisao. Para cada par, compara:

- numero de titulos (linhas que comecam com #, fora de bloco de codigo)
- numero de blocos de codigo (```)
- o seletor de idioma na primeira linha

NAO confere se a traducao esta certa; isso e revisao humana. Pega o erro comum:
mudar um idioma e esquecer o outro. Uma secao nova so de um lado muda a contagem
de titulos; um exemplo novo so de um lado muda a de blocos.

So biblioteca padrao, como os testes: o CI nao precisa de mais que o interpretador.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SO_INGLES = {"CHANGELOG.md"}
SUFIXO = ".pt-BR.md"


def estrutura(texto: str) -> tuple[int, int]:
    titulos = blocos = 0
    dentro = False
    for linha in texto.splitlines():
        if linha.lstrip().startswith("```"):
            blocos += 1
            dentro = not dentro
        elif not dentro and linha.startswith("#"):
            titulos += 1
    return titulos, blocos


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    # So o que o git conhece: arquivo de rascunho local nao deveria reprovar ninguem.
    arquivos = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard",
                               "*.md"], cwd=raiz, capture_output=True, text=True, check=True).stdout.split()
    # .github/ fica de fora: o GitHub mostra cada modelo de issue como opcao propria,
    # e um par EN/PT viraria dois modelos na tela de "New issue".
    md = {Path(a) for a in arquivos if (raiz / a).is_file() and not a.startswith(".github/")}
    erros = []

    for pt in sorted(p for p in md if p.name.endswith(SUFIXO)):
        en = pt.with_name(pt.name[: -len(SUFIXO)] + ".md")
        if en not in md:
            erros.append(f"{pt}: sem o par em ingles ({en})")

    for en in sorted(p for p in md if not p.name.endswith(SUFIXO)):
        if en.name in SO_INGLES and en.parent == Path("."):
            continue
        pt = en.with_name(en.stem + SUFIXO)
        if pt not in md:
            erros.append(f"{en}: sem o par em portugues ({pt})")
            continue
        t_en, t_pt = (raiz / en).read_text(encoding="utf-8"), (raiz / pt).read_text(encoding="utf-8")
        (h_en, b_en), (h_pt, b_pt) = estrutura(t_en), estrutura(t_pt)
        if h_en != h_pt:
            erros.append(f"{en} / {pt}: titulos {h_en} x {h_pt}")
        if b_en != b_pt:
            erros.append(f"{en} / {pt}: blocos de codigo {b_en} x {b_pt}")
        if pt.name not in t_en.splitlines()[0]:
            erros.append(f"{en}: a 1a linha nao tem o seletor apontando para {pt.name}")
        if en.name not in t_pt.splitlines()[0]:
            erros.append(f"{pt}: a 1a linha nao tem o seletor apontando para {en.name}")

    for e in erros:
        print(e, file=sys.stderr)
    if not erros:
        print(f"ok: {sum(1 for p in md if p.name.endswith(SUFIXO))} pares EN/PT-BR em sincronia estrutural")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
