# O que atravessa o dbusmenu — e o que não

Este documento existe porque cinco bugs deste projeto tiveram a mesma causa, e eu
tratei cada um como problema separado antes de encontrá-la.

## A causa

`libappindicator3` linka `libdbusmenu-gtk3`:

```
$ ldd /usr/lib/x86_64-linux-gnu/libappindicator3.so.1 | grep dbusmenu
libdbusmenu-gtk3.so.4 => /lib/x86_64-linux-gnu/libdbusmenu-gtk3.so.4
libdbusmenu-glib.so.4 => /lib/x86_64-linux-gnu/libdbusmenu-glib.so.4
```

**O menu não é desenhado pelo GTK na máquina do usuário.** Ele é serializado por
D-Bus e renderizado pelo *shell*. O programa é o servidor; quem desenha é outro
processo, possivelmente com outro toolkit.

Só trafegam as propriedades que o protocolo define:

```
label · enabled · visible · icon-name · icon-data
toggle-type · toggle-state · children-display
shortcut · disposition · accessible-desc
```

## O que NÃO atravessa

Widget nenhum. Foram tentados e falharam, todos pelo mesmo motivo:

| Tentativa | Resultado |
|---|---|
| `Gtk.Box` aninhada com título, barra e detalhe | linha inteira invisível |
| `Gtk.Label` alinhado à direita dentro de uma caixa | invisível |
| `Gtk.ProgressBar` dentro de caixa | invisível |
| `Gtk.ProgressBar` como filha direta, insensível | invisível |
| `Gtk.ProgressBar` como filha direta, sensível | invisível |
| `Gtk.Image` como filho de `Gtk.MenuItem` | invisível |

Não adianta tentar outro arranjo. A regra que sobra: **cada item é um
`Gtk.Label`, e o que se vê é o texto dele.**

Por isso a barra de progresso é desenhada com caracteres, e não com
`Gtk.ProgressBar`. Não é escolha estética.

## O que atravessa, e como

**Ícone** — sim, mas pela propriedade, não pelo widget. A ponte lê a propriedade
`image` de um **`Gtk.ImageMenuItem`** (`gtk_image_menu_item_get_type` aparece nos
símbolos da `libdbusmenu-gtk3`) e traduz para `icon-name` do protocolo.

`ImageMenuItem` é obsoleto no GTK 3 e emite aviso — mas é o único widget que a
ponte reconhece, e o alvo aqui é o protocolo, não o GTK.

**Submenu** — sim, via `children-display`. É a única forma de agrupar ações.

**Markup do Pango** — é interpretado **localmente** e só o texto resultante é
enviado. Então `<b>` e `<span foreground>` não chegam do outro lado: negrito,
cor e tamanho **não existem** neste menu.

Consequência prática: hierarquia visual sai de recuo, símbolo e separador. E cor
de status vem de **emoji**, que são glifos coloridos pela fonte, não texto
colorido pelo tema.

## Tooltip não existe

```
$ strings libdbusmenu-glib.so.4 libdbusmenu-gtk3.so.4 | grep -ci tooltip
0
```

Não é limitação de implementação nem do GNOME: o protocolo não tem o conceito.
Informação que se quereria no *hover* precisa estar no rótulo — é por isso que as
seções acionáveis anunciam "CLIQUE PARA VARRER" no próprio título.

## `disposition` existe, mas é inalcançável daqui

O protocolo define `normal / informative / warning / alert`, o que seria destaque
semântico sem depender de cor manual. Os símbolos existem na biblioteca:

```
genericmenuitem_set_disposition
genericmenuitem_get_disposition
```

Mas são do lado **cliente** — usados quando a biblioteca *recebe* um menu e monta
widgets. Nós somos o servidor: construímos um `GtkMenu` e a ponte converte. Não
há API GTK de onde ela pudesse derivar `disposition`.

Quem quiser usá-lo precisa falar dbusmenu direto, sem a ponte GTK. A migração
para [`ksni`](https://crates.io/crates/ksni) descrita no [ROADMAP](../ROADMAP.md)
poderá fazer isso.

## Por que isto está documentado

Cada um dos cinco bugs acima recebeu, na hora, uma explicação plausível e errada
— negociação de largura, esmaecimento do insensível, tema escuro. As explicações
eram razoáveis e nenhuma era a causa.

A evidência decisiva esteve visível o tempo todo e passou despercebida: **os
ícones dos itens de ação também não apareciam**. Dois tipos de widget falhando
ao mesmo tempo apontavam para uma fronteira, não para dois bugs.
