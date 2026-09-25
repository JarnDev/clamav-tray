"""Linhas do menu.

Separado de tray.py de proposito: aqui nao ha systemd, nem ClamAV, nem politica —
so como uma linha se parece. E a parte que NAO vai para Rust (a camada grafica
sera reescrita com ksni, que tem outro modelo de menu), entao mante-la isolada
evita que decisao de aparencia contamine a logica.

GTK 3 permite trocar o filho de um Gtk.MenuItem por qualquer widget. Um menu de
bandeja moderno nao e uma lista de strings: e um bloco com titulo, valor alinhado
a direita e detalhe secundario menor.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango  # noqa: E402

# Paleta Adwaita. Cor fixa em vez de tema porque um ponto de status precisa
# significar a mesma coisa em qualquer tema — inclusive claro e escuro.
GREEN = "#2ec27e"
RED = "#e01b24"
AMBER = "#f5c211"
BLUE = "#3584e4"
DIM = "#9a9996"

DOT = "●"


def dot(color: str) -> str:
    return f'<span foreground="{color}" size="large">{DOT}</span>'


def header(title: str, subtitle: str, color: str) -> Gtk.MenuItem:
    """Bloco de topo: diz o veredito antes de o usuario ler qualquer linha."""
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    box.set_margin_top(4)
    box.set_margin_bottom(4)

    top = Gtk.Label(xalign=0)
    top.set_markup(f'{dot(color)}  <b>{_esc(title)}</b>')
    box.pack_start(top, False, False, 0)

    if subtitle:
        sub = Gtk.Label(xalign=0)
        sub.set_markup(f'<span foreground="{DIM}" size="small">{_esc(subtitle)}</span>')
        sub.set_margin_start(20)
        box.pack_start(sub, False, False, 0)

    item.add(box)
    return item


def status_row(label: str, value: str, color: str, detail: str = "") -> Gtk.MenuItem:
    """Nome a esquerda, estado a direita, detalhe embaixo em cinza.

    O alinhamento a direita e o que faz a coluna de estados virar coluna de
    verdade, legivel de relance, em vez de texto corrido.
    """
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    left = Gtk.Label(xalign=0)
    left.set_markup(f"{dot(color)}  {_esc(label)}")
    left.set_ellipsize(Pango.EllipsizeMode.END)
    line.pack_start(left, True, True, 0)

    right = Gtk.Label(xalign=1)
    right.set_markup(f'<span foreground="{DIM}" size="small">{_esc(value)}</span>')
    line.pack_end(right, False, False, 0)
    outer.pack_start(line, False, False, 0)

    if detail:
        sub = Gtk.Label(xalign=0)
        sub.set_markup(f'<span foreground="{DIM}" size="small">{_esc(detail)}</span>')
        sub.set_margin_start(20)
        outer.pack_start(sub, False, False, 0)

    item.add(outer)
    return item


def progress_row(label: str, fraction: float | None, detail: str) -> Gtk.MenuItem:
    """Barra para varredura em andamento.

    `fraction=None` vira barra pulsante: o clamdscan nao informa progresso, e
    fingir uma porcentagem seria inventar. Pulsar diz "esta vivo" sem mentir
    quanto falta.
    """
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    box.set_margin_top(2)
    box.set_margin_bottom(2)

    top = Gtk.Label(xalign=0)
    top.set_markup(f'{dot(BLUE)}  <b>{_esc(label)}</b>')
    box.pack_start(top, False, False, 0)

    bar = Gtk.ProgressBar()
    bar.set_margin_start(20)
    if fraction is None:
        bar.pulse()
    else:
        bar.set_fraction(max(0.0, min(1.0, fraction)))
    box.pack_start(bar, False, False, 0)

    if detail:
        sub = Gtk.Label(xalign=0)
        sub.set_markup(f'<span foreground="{DIM}" size="small">{_esc(detail)}</span>')
        sub.set_margin_start(20)
        box.pack_start(sub, False, False, 0)

    item.add(box)
    return item


def section(title: str) -> Gtk.MenuItem:
    """Rotulo de secao: maiusculas pequenas em cinza, como painel de sistema."""
    item = Gtk.MenuItem()
    item.set_sensitive(False)
    lbl = Gtk.Label(xalign=0)
    lbl.set_markup(
        f'<span foreground="{DIM}" size="x-small" letter_spacing="1200">'
        f"{_esc(title.upper())}</span>"
    )
    lbl.set_margin_top(6)
    item.add(lbl)
    return item


def action(label: str, icon_name: str, handler) -> Gtk.MenuItem:
    """Acao com icone do tema, em vez de emoji."""
    item = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.pack_start(
        Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU), False, False, 0
    )
    box.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
    item.add(box)
    item.connect("activate", handler)
    return item


def separator() -> Gtk.SeparatorMenuItem:
    return Gtk.SeparatorMenuItem()


def _esc(text: str) -> str:
    """Pango falha silenciosamente com markup invalido; nome de unidade pode ter &."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
