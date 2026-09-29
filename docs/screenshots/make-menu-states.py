#!/usr/bin/env python3
"""Gera docs/screenshots/menu-states.png.

Irmão de make-tray-states.py, e existe pelo mesmo motivo: o HTML que produziu a
primeira versão morava num diretório temporário, então a imagem não era
corrigível — só refazível do zero.

A barra de progresso é montada com as CONSTANTES DO PRODUTO, lidas do código de
`widgets.py`. Não é preciosismo: a barra é desenhada com caracteres porque nenhum
widget atravessa o dbusmenu (ver docs/dbusmenu.md), então o que aparece no menu de
verdade é exatamente esta string. Se a imagem trouxesse os caracteres digitados à
mão, ela poderia divergir do programa sem ninguém notar — que é o defeito que
imagem de README costuma ter.

As constantes são lidas do TEXTO do módulo, e não por import, para o gerador não
exigir GTK: quem for regenerar a imagem pode não ter o ambiente gráfico montado.

Uso:
    python3 docs/screenshots/make-menu-states.py

Requer: google-chrome (ou chromium) e Pillow.
"""

from __future__ import annotations

import ast
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
WIDGETS = RAIZ.parent.parent / "clamav_tray" / "widgets.py"

VERDE, AZUL, AMARELO, VERMELHO, LARANJA = "🟢", "🔵", "🟡", "🔴", "🟠"


def _constante(nome: str):
    """Lê `NOME = <literal>` do código de widgets.py."""
    fonte = WIDGETS.read_text(encoding="utf-8")
    if m := re.search(rf"^{nome}\s*=\s*(.+)$", fonte, re.M):
        return ast.literal_eval(m.group(1).strip())
    sys.exit(f"nao achei {nome} em {WIDGETS}")


def barra(fracao: float) -> str:
    """Mesma regra de widgets.progress_bar: int(), nunca round().

    Com arredondamento, 99% enchia a barra e ela dizia "acabou" antes de acabar.
    """
    cheio, vazio, celulas = (
        _constante("BAR_FULL"), _constante("BAR_EMPTY"), _constante("BAR_CELLS"))
    pct = max(0.0, min(1.0, fracao))
    n = celulas if pct >= 1.0 else min(int(pct * celulas), celulas - 1)
    return f"{cheio * n}{vazio * (celulas - n)}  {int(pct * 100)}%"


# ----------------------------------------------------------------- conteudo

SISTEMA_OK = [
    ("sec", "SISTEMA"),
    ("inf", VERDE, "ClamAV Daemon", ""),
    ("inf", VERDE, "Freshclam", ""),
    ("inf", VERDE, "Monitor de Downloads", ""),
]
RODAPE = [("hr",), ("act", "", "Ver logs", ""), ("act", "", "Configurações", ""),
          ("hr",), ("act", "", "Sair", "")]

MENUS = [
    ("Protegido", [
        ("inf", VERDE, "Protegido", ""),
        ("det", "Última varredura hoje 07:42"),
        ("det", "Limpa (4h31), 6 arquivos ilegíveis"),
        ("det", "Próxima amanhã 03:03"),
        ("hr",), *SISTEMA_OK, ("hr",),
        ("sec", "USUÁRIO · CLIQUE PARA VARRER"),
        ("act", VERDE, "Varrer a home", "sem ameaças ontem 21:40"),
        ("hr",),
        ("sec", "QUARENTENA · CLIQUE PARA LISTAR"),
        ("act", VERDE, "root", "vazia"),
        ("det", "/var/quarantine/clamav"),
        ("act", VERDE, "user", "vazia"),
        ("det", "~/.local/share/clamav-tray/quarantine"),
        *RODAPE,
    ]),
    ("Varredura em andamento", [
        ("inf", AZUL, "Varredura em andamento", ""),
        ("bar", barra(0.37)),
        ("det", "412.391 de 1.131.805 arquivos"),
        ("det", "1h20 · 85/s · faltam 719.414"),
        ("det", "Nenhum infectado"),
        ("det", "Alvo  ~"),
        ("hr",), *SISTEMA_OK, ("hr",),
        ("sec", "USUÁRIO · CLIQUE PARA PARAR"),
        ("act", AZUL, "Varredura sob demanda", "em andamento"),
        ("hr",),
        ("sec", "QUARENTENA · CLIQUE PARA LISTAR"),
        ("act", VERDE, "root", "vazia"),
        ("act", VERDE, "user", "vazia"),
        *RODAPE,
    ]),
    ("Mídia por varrer", [
        ("inf", VERDE, "Protegido", ""),
        ("det", "Última varredura hoje 07:42"),
        ("det", "Limpa (4h31), 6 arquivos ilegíveis"),
        ("det", "Próxima amanhã 03:03"),
        ("hr",), *SISTEMA_OK, ("hr",),
        ("sec", "USUÁRIO · CLIQUE PARA VARRER"),
        ("act", VERDE, "Varrer a home", "sem ameaças ontem 21:40"),
        ("hr",),
        ("sec", "DISPOSITIVOS · CLIQUE PARA VARRER"),
        ("act", AMARELO, "KINGSTON", "14,9 GB · não varrido"),
        ("det", "/media/user/KINGSTON"),
        ("act", VERDE, "BACKUP", "1,8 TB · limpo hoje 18:02"),
        ("det", "/media/user/BACKUP"),
        ("hr",),
        ("sec", "QUARENTENA · CLIQUE PARA LISTAR"),
        ("act", VERDE, "root", "vazia"),
        ("act", VERDE, "user", "vazia"),
        *RODAPE,
    ]),
    ("Ameaça detectada", [
        ("inf", VERMELHO, "Ameaça detectada", ""),
        ("det", "2 arquivos em quarentena"),
        ("det", "Última varredura hoje 07:42"),
        ("det", "Limpa (4h31), 6 arquivos ilegíveis"),
        ("det", "Próxima amanhã 03:03"),
        ("hr",),
        ("sec", "SISTEMA"),
        ("inf", VERDE, "ClamAV Daemon", ""),
        ("inf", LARANJA, "Freshclam · failed", ""),
        ("inf", VERDE, "Monitor de Downloads", ""),
        ("hr",),
        ("sec", "USUÁRIO · CLIQUE PARA VARRER"),
        ("act", VERDE, "Varrer a home", "sem ameaças ontem 21:40"),
        ("hr",),
        ("sec", "DISPOSITIVOS · CLIQUE PARA VARRER"),
        ("act", VERMELHO, "KINGSTON", "14,9 GB · 1 ameaça NÃO isolada hoje 19:28"),
        ("det", "/media/user/KINGSTON"),
        ("hr",),
        ("sec", "QUARENTENA · CLIQUE PARA LISTAR"),
        ("act", LARANJA, "root", "1 arquivo · 14 MB"),
        ("det", "conferido hoje 07:42"),
        ("act", LARANJA, "user", "1 arquivo"),
        ("det", "~/.local/share/clamav-tray/quarantine"),
        *RODAPE,
    ]),
]

CSS = """
:root { color-scheme: only dark; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #17171a; padding: 30px 26px; display: flex; gap: 24px;
  align-items: flex-start; font-family: Ubuntu, Cantarell, system-ui, sans-serif;
}
.col { display: flex; flex-direction: column; gap: 11px; }
.cap {
  color: #aca8a4; font-size: 11.5px; letter-spacing: .09em;
  text-transform: uppercase; padding-left: 4px;
}
.menu {
  width: 352px; background: #353535; border: 1px solid #4a4a4a; border-radius: 12px;
  padding: 8px 0; color: #eceae7; font-size: 13.5px; box-shadow: 0 10px 30px rgba(0,0,0,.6);
}
.inf, .act { padding: 5px 16px; }
.val { color: #bfbbb7; }
.det { padding: 2px 16px 2px 44px; color: #bfbbb7; font-size: 12.5px; }
/* A barra e texto: fonte monoespacada para as celulas ficarem do mesmo tamanho, e
   cor CHEIA — o trilho ja e mais claro que o fundo pelo proprio glifo. */
.bar {
  padding: 3px 16px 5px 44px; font-family: "Ubuntu Mono", "DejaVu Sans Mono", monospace;
  font-size: 13px; color: #eceae7;
}
.sec { padding: 8px 16px 3px; color: #aca8a4; font-size: 10.5px; letter-spacing: .13em; }
.hr { height: 1px; background: #4f4f4f; margin: 6px 14px; }
"""


def monta_html() -> str:
    colunas = []
    for titulo, linhas in MENUS:
        corpo = []
        for linha in linhas:
            tipo = linha[0]
            if tipo == "hr":
                corpo.append('<div class="hr"></div>')
            elif tipo == "sec":
                corpo.append(f'<div class="sec">{html.escape(linha[1])}</div>')
            elif tipo == "det":
                corpo.append(f'<div class="det">{html.escape(linha[1])}</div>')
            elif tipo == "bar":
                corpo.append(f'<div class="bar">{html.escape(linha[1])}</div>')
            else:
                _, ponto, rotulo, valor = linha
                prefixo = f"{ponto}  " if ponto else ""
                extra = f'   <span class="val">{html.escape(valor)}</span>' if valor else ""
                corpo.append(
                    f'<div class="{tipo}">{prefixo}{html.escape(rotulo)}{extra}</div>')
        colunas.append(
            f'<div class="col"><div class="cap">{html.escape(titulo)}</div>'
            f'<div class="menu">{"".join(corpo)}</div></div>')
    return f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{''.join(colunas)}"


def _navegador() -> str:
    for exe in ("google-chrome", "chromium", "chromium-browser"):
        if caminho := shutil.which(exe):
            return caminho
    sys.exit("nenhum chrome/chromium no PATH")


def main() -> int:
    saida = RAIZ / "menu-states.png"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pagina = tmp / "menu-states.html"
        pagina.write_text(monta_html(), encoding="utf-8")
        bruta = tmp / "bruta.png"
        subprocess.run([
            _navegador(), "--headless", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2",
            # Janela alta: o headless corta a base quando ela e justa.
            "--window-size=1600,1100",
            f"--screenshot={bruta}", pagina.as_uri(),
        ], check=True, capture_output=True, timeout=120)

        from PIL import Image
        im = Image.open(bruta).convert("RGB")
        fundo = im.getpixel((2, 2))
        larg, alt = im.size
        pixels = im.load()

        def vazia(y: int) -> bool:
            return all(pixels[x, y] == fundo for x in range(0, larg, 3))

        topo, base = 0, alt - 1
        while topo < alt and vazia(topo):
            topo += 1
        while base > topo and vazia(base):
            base -= 1
        margem = 30
        im.crop((0, max(0, topo - margem), larg, min(alt, base + margem + 1))).save(saida)

    print(f"escrito: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
