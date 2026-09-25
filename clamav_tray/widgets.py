"""Linhas do menu.

Separado de tray.py de proposito: aqui nao ha systemd, nem ClamAV, nem politica —
so como uma linha se parece. E a parte que NAO vai para Rust (a camada grafica
sera reescrita com ksni, que tem outro modelo de menu), entao mante-la isolada
evita que decisao de aparencia contamine a logica.

DUAS LICOES PAGAS COM BUG, que explicam por que o codigo aqui e mais simples do
que a primeira versao:

1. Linha informativa usa `set_sensitive(False)`. E o unico jeito de o GTK nao
   destacar no hover nem aceitar clique. O efeito colateral e esmaecer o texto —
   e isso SOBREPOE `foreground` de markup Pango, deixando todo ponto de status
   cinza. A saida nao e abrir mao do insensivel: e usar EMOJI como ponto. Emoji
   sao glifos coloridos pela fonte, entao a cor sobrevive ao esmaecimento.

2. Caixa aninhada dentro de Gtk.MenuItem nao negocia largura de forma confiavel:
   o rotulo alinhado a direita e a linha de detalhe simplesmente nao apareciam.
   Cada linha agora e UM Gtk.Label com markup, podendo conter quebra de linha.
   Perde-se o alinhamento a direita; ganha-se aparecer.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

# Cinza para texto secundario. Sobrevive porque e apenas *mais* apagado que o
# esmaecimento do GTK, nunca mais vivo.
DIM = "#9a9996"

# Nomes de estado, nao de cor: quem chama nao deveria escolher "verde", e sim
# dizer que esta tudo bem. Trocar o simbolo depois nao mexe em tray.py.
OK = "🟢"
WARN = "🟠"
BAD = "🔴"
BUSY = "🔵"
IDLE = "⚪"


def header(title: str, subtitle: str, mark: str) -> Gtk.MenuItem:
    """Bloco de topo: diz o veredito antes de o usuario ler qualquer linha."""
    markup = f"{mark}  <b>{_esc(title)}</b>"
    if subtitle:
        markup += f'\n<span foreground="{DIM}" size="small">     {_esc(subtitle)}</span>'
    return _info_item(markup)


def status_row(label: str, value: str, mark: str, detail: str = "") -> Gtk.MenuItem:
    """Ponto, nome, valor secundario e — opcionalmente — detalhe embaixo."""
    markup = f"{mark}  {_esc(label)}"
    if value:
        markup += f'   <span foreground="{DIM}" size="small">{_esc(value)}</span>'
    if detail:
        markup += f'\n<span foreground="{DIM}" size="small">     {_esc(detail)}</span>'
    return _info_item(markup)


def progress_row(label: str, fraction: float | None, detail: str) -> Gtk.MenuItem:
    """Varredura em andamento, com barra de progresso.

    `fraction=None` vira barra pulsante: o clamdscan nao informa progresso, e
    fingir uma porcentagem seria inventar. Pulsar diz "esta vivo" sem mentir
    quanto falta.
    """
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

    top = Gtk.Label(xalign=0)
    top.set_markup(f"{BUSY}  <b>{_esc(label)}</b>")
    box.pack_start(top, False, False, 0)

    bar = Gtk.ProgressBar()
    bar.set_size_request(240, -1)   # menu de bandeja e estreito; sem isto a barra some
    if fraction is None:
        # Sem fracao a barra PULSA. O clamdscan nao informa progresso quando se
        # aponta um diretorio; fingir porcentagem seria inventar.
        bar.pulse()
    else:
        bar.set_fraction(max(0.0, min(1.0, fraction)))
        bar.set_show_text(True)
        bar.set_text(f"{int(fraction * 100)}%")
    box.pack_start(bar, False, False, 0)

    if detail:
        sub = Gtk.Label(xalign=0)
        sub.set_markup(f'<span foreground="{DIM}" size="small">{_esc(detail)}</span>')
        box.pack_start(sub, False, False, 0)

    item.add(box)
    return item


def section(title: str) -> Gtk.MenuItem:
    """Rotulo de secao: maiusculas pequenas em cinza, como painel de sistema."""
    return _info_item(
        f'<span foreground="{DIM}" size="x-small" letter_spacing="1500">'
        f"{_esc(title.upper())}</span>"
    )


def action(label: str, icon_name: str, handler) -> Gtk.MenuItem:
    """Acao com icone do tema. Sensivel de proposito: esta SIM e clicavel, e a
    diferenca de comportamento no hover e o que distingue as duas coisas."""
    item = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box.pack_start(
        Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU), False, False, 0
    )
    box.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
    item.add(box)
    item.connect("activate", handler)
    return item


def separator() -> Gtk.SeparatorMenuItem:
    return Gtk.SeparatorMenuItem()


def _info_item(markup: str) -> Gtk.MenuItem:
    """Uma linha que informa e nao reage.

    `set_sensitive(False)` e o que remove destaque no hover e clique. O preco e o
    esmaecimento — aceitavel porque o unico elemento que PRECISA de cor e o ponto,
    e ele e emoji.
    """
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    lbl = Gtk.Label(xalign=0)
    lbl.set_markup(markup)
    lbl.set_line_wrap(False)
    item.add(lbl)
    return item


def _esc(text: str) -> str:
    """Pango falha silenciosamente com markup invalido; nome de unidade pode ter &."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
