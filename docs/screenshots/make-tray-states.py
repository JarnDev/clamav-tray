#!/usr/bin/env python3
"""Gera docs/screenshots/tray-states.png.

Existe porque a primeira versao desta imagem era ILEGIVEL e ninguem tinha como
refaze-la: o HTML morava num diretorio temporario.

O defeito que motivou o script:

    <svg fill="currentColor">
      <path ... fill="#2e3436"/>     <- vence o currentColor

Os simbolicos do Adwaita trazem esse `fill` embutido. O GTK o ignora e recolore o
icone (e a convencao do sufixo `-symbolic`); um NAVEGADOR nao. Renderizando o SVG
cru no HTML, os cinco icones sairam em #2e3436 sobre pilula #3d3d3d — medido,
1,16:1, contra o minimo de 3:1 da WCAG para elemento grafico. Azul-escuro sobre
cinza-escuro, exatamente o que se reclamou.

Por isso `_limpa_fill` remove o atributo antes de inserir o SVG na pagina.

Os icones sao BRANCOS, e nao verde/vermelho, porque e assim que aparecem de
verdade: o indicador pede um icone pelo NOME (`security-high-symbolic`) e quem
pinta e o shell, com a cor de primeiro plano do painel. Colorir aqui deixaria a
imagem mais bonita e mentiria sobre o produto — os estados se distinguem pela
FORMA e pelo rotulo ao lado, que e o que o usuario realmente ve.

Uso:
    python3 docs/screenshots/make-tray-states.py

Requer: google-chrome (ou chromium) e Pillow.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
TEMAS = [
    Path("/usr/share/icons/Adwaita/symbolic"),
    Path("/usr/share/icons/Adwaita/scalable"),
]

# Mesmos nomes que clamav_tray/tray.py pede ao tema. Se divergirem, a imagem passa
# a documentar um programa que nao existe.
ESTADOS = [
    ("security-high-symbolic", "", "Protegido", "tudo no ar, nada pendente"),
    ("system-search-symbolic", "37%", "Varrendo", "porcentagem contada, não estimada"),
    ("media-removable-symbolic", "⚠", "Mídia por varrer", "pendrive plugado, ainda não varrido"),
    ("security-medium-symbolic", "⚠", "Serviço caído", "daemon ou freshclam parado"),
    ("security-low-symbolic", "⚠ 3", "Ameaça", "encontrada na última varredura"),
]

# Cor do primeiro plano do painel do GNOME. Branco puro sobre a pilula clara do
# hover da ~12:1 — o oposto do 1,16:1 que havia aqui.
CSS = """
:root { color-scheme: only dark; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #17171a;
  padding: 32px 26px;
  font-family: Ubuntu, Cantarell, system-ui, sans-serif;
  display: flex;
  gap: 22px;
  align-items: flex-start;
}
.cell { display: flex; flex-direction: column; align-items: center; gap: 13px; width: 200px; }
/* A barra superior do GNOME e mais escura que a area de trabalho. Reproduzir isso
   e o que faz a pilula do indicador parecer o que e. */
.panel {
  width: 100%;
  background: #0d0d0f;
  border-radius: 10px;
  border: 1px solid #2a2a2e;
  padding: 7px;
  display: flex;
  justify-content: center;
}
.pill {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255, 255, 255, .13);
  border-radius: 20px;
  padding: 7px 14px;
  color: #ffffff;
}
.pill svg { width: 22px; height: 22px; display: block; }
.lab { font-size: 14px; font-weight: 500; line-height: 1; }
.nome { color: #f4f2f0; font-size: 14.5px; font-weight: 600; }
.desc { color: #a9a5a1; font-size: 12.5px; text-align: center; line-height: 1.45; }
"""

_FILL = re.compile(r'\sfill="(?!none)[^"]*"')


def _limpa_fill(svg: str) -> str:
    """Tira o `fill` embutido para o `currentColor` do CSS valer.

    `fill="none"` e preservado: em alguns icones ele marca area que deve ficar
    vazada, e apaga-lo encheria o desenho.
    """
    svg = re.sub(r"<\?xml.*?\?>", "", svg, flags=re.S)
    svg = _FILL.sub("", svg)
    return svg.replace("<svg", '<svg fill="currentColor"', 1)


def _acha_icone(nome: str) -> Path:
    for base in TEMAS:
        if achados := list(base.rglob(f"{nome}.svg")):
            return achados[0]
    sys.exit(f"icone '{nome}' nao encontrado — instale o tema Adwaita (adwaita-icon-theme)")


def monta_html() -> str:
    celulas = []
    for nome_icone, rotulo, titulo, desc in ESTADOS:
        svg = _limpa_fill(_acha_icone(nome_icone).read_text(encoding="utf-8"))
        lab = f'<span class="lab">{rotulo}</span>' if rotulo else ""
        celulas.append(
            f'<div class="cell"><div class="panel"><span class="pill">{svg}{lab}</span></div>'
            f'<div class="nome">{titulo}</div><div class="desc">{desc}</div></div>'
        )
    return f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{''.join(celulas)}"


def _navegador() -> str:
    for exe in ("google-chrome", "chromium", "chromium-browser"):
        if caminho := shutil.which(exe):
            return caminho
    sys.exit("nenhum chrome/chromium no PATH")


def main() -> int:
    saida = RAIZ / "tray-states.png"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pagina = tmp / "tray-states.html"
        pagina.write_text(monta_html(), encoding="utf-8")
        bruta = tmp / "bruta.png"
        subprocess.run([
            _navegador(), "--headless", "--disable-gpu", "--hide-scrollbars",
            # 2x: a imagem e vista ampliada no README, e icone simbolico a 1x
            # perde a forma — que aqui e o que distingue um estado do outro.
            "--force-device-scale-factor=2",
            # Janela ALTA de proposito: o headless corta a base da pagina, e o
            # recorte abaixo devolve o tamanho certo.
            "--window-size=1160,600",
            f"--screenshot={bruta}", pagina.as_uri(),
        ], check=True, capture_output=True, timeout=120)

        from PIL import Image
        im = Image.open(bruta).convert("RGB")
        # Recorta pela altura do CONTEUDO. A janela e alta de proposito (o headless
        # corta a base se ela for justa), entao sobra fundo embaixo; achar a
        # primeira e a ultima linha que diferem do fundo devolve o tamanho certo
        # sem fixar numero nenhum, que quebraria ao mexer no texto.
        fundo = im.getpixel((2, 2))
        larg, alt = im.size
        pixels = im.load()
        vazia = lambda y: all(pixels[x, y] == fundo for x in range(0, larg, 3))
        topo, base = 0, alt - 1
        while topo < alt and vazia(topo):
            topo += 1
        while base > topo and vazia(base):
            base -= 1
        margem = 28
        im.crop((0, max(0, topo - margem), larg, min(alt, base + margem + 1))).save(saida)

    print(f"escrito: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
