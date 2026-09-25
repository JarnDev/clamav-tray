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

2. ESTE MENU NAO E DESENHADO PELO GTK. O libappindicator linka libdbusmenu-gtk3:
   o menu e serializado por D-Bus e renderizado pelo SHELL. So trafegam as
   propriedades que o protocolo dbusmenu define — rotulo, habilitado, visivel.

   Widget nenhum atravessa. Caixa aninhada, rotulo alinhado a direita, Gtk.Image
   em item de acao e Gtk.ProgressBar: todos foram tentados, nenhum apareceu. Nao
   adianta insistir com arranjo diferente.

   A regra que sobra: cada item e UM Gtk.Label, e o que se ve e o TEXTO dele.
   Barra de progresso, portanto, e desenhada com caracteres.
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


# A barra e DESENHADA COM CARACTERES, nao com Gtk.ProgressBar. Ver a nota sobre
# dbusmenu no topo deste arquivo: widget nenhum atravessa o protocolo.
BAR_FULL = "█"
BAR_EMPTY = "░"
BAR_CELLS = 22


def progress_bar(fraction: float | None) -> Gtk.MenuItem:
    """Barra de progresso em blocos Unicode.

    Nao e escolha estetica: e a unica forma que existe. Um Gtk.ProgressBar dentro
    de um menu de AppIndicator nunca aparece, porque o menu viaja por dbusmenu e
    so o TEXTO do rotulo chega do outro lado.

    Sem fracao, mostra um traco continuo em vez de porcentagem — nao da para
    pulsar sem widget, e inventar numero seria pior.
    """
    if fraction is None:
        return _info_item(f"     {BAR_EMPTY * BAR_CELLS}  —")
    pct = max(0.0, min(1.0, fraction))
    # int() e nao round(): com arredondamento, 99% enchia a barra inteira e ela
    # dizia "acabou" antes de acabar. So 100% completa.
    filled = BAR_CELLS if pct >= 1.0 else min(int(pct * BAR_CELLS), BAR_CELLS - 1)
    bar = BAR_FULL * filled + BAR_EMPTY * (BAR_CELLS - filled)
    return _info_item(f"     {bar}  {int(pct * 100)}%")


def card_line(label: str, value: str, mark: str = "") -> Gtk.MenuItem:
    """Linha de detalhe do card: recuada, sem ponto, valor em destaque."""
    prefix = f"{mark}  " if mark else "     "
    return _info_item(
        f'{prefix}<span foreground="{DIM}" size="small">{_esc(label)}</span>'
        f'  <b><span size="small">{_esc(value)}</span></b>'
    )


def section(title: str) -> Gtk.MenuItem:
    """Rotulo de secao: maiusculas pequenas em cinza, como painel de sistema."""
    return _info_item(
        f'<span foreground="{DIM}" size="x-small" letter_spacing="1500">'
        f"{_esc(title.upper())}</span>"
    )


def action(label: str, icon_name: str, handler) -> Gtk.MenuItem:
    """Acao clicavel, com icone quando houver.

    O icone precisa vir de `Gtk.ImageMenuItem`, nao de um `Gtk.Image` colocado
    como filho: a ponte GTK->dbusmenu le a propriedade `image` DESTE widget
    (`gtk_image_menu_item_get_type` aparece nos simbolos da libdbusmenu-gtk3) e a
    traduz para a propriedade `icon-name` do protocolo. Widget filho nao atravessa;
    propriedade do protocolo, sim.

    ImageMenuItem e obsoleto no GTK 3 e emite aviso — mas e o unico widget que a
    ponte reconhece, e o alvo aqui e o protocolo, nao o GTK.
    """
    if not icon_name:
        item = Gtk.MenuItem(label=label)
        item.connect("activate", handler)
        return item

    item = Gtk.ImageMenuItem(label=label)
    item.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU))
    item.set_always_show_image(True)
    item.connect("activate", handler)
    return item


def status_action(label: str, value: str, mark: str, handler) -> Gtk.MenuItem:
    """Linha de estado que TAMBEM e acao.

    Existe porque um item separado so para "listar" repetia o que a linha da
    quarentena ja nomeia. Clicar no proprio item e mais curto e nao exige que o
    usuario ligue duas entradas do menu mentalmente.

    O realce no hover, que nas linhas informativas e ruido, aqui e a affordance:
    e o que distingue o que responde ao clique do que so informa.
    """
    markup = f"{mark}  {_esc(label)}"
    if value:
        markup += f'   <span foreground="{DIM}" size="small">{_esc(value)}</span>'
    item = Gtk.MenuItem()
    lbl = Gtk.Label(xalign=0)
    lbl.set_markup(markup)
    item.add(lbl)
    item.connect("activate", handler)
    return item


def submenu(label: str, entries: list[tuple[str, object]]) -> Gtk.MenuItem:
    """Item que abre um submenu.

    Submenu ATRAVESSA o dbusmenu — ele faz parte do protocolo
    (`children-display: submenu`), ao contrario de widget filho. E a unica forma
    de agrupar acoes neste tipo de menu.
    """
    item = Gtk.MenuItem(label=label)
    sub = Gtk.Menu()
    for text, handler in entries:
        child = Gtk.MenuItem(label=text)
        child.connect("activate", handler)
        sub.append(child)
    sub.show_all()
    item.set_submenu(sub)
    return item


def line(text: str) -> Gtk.MenuItem:
    """Linha de detalhe, recuada. O recuo e feito com espacos porque nao ha
    margem que atravesse o dbusmenu."""
    return _info_item("     " + _esc(text))


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
