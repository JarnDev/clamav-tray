**English** · [Português (Brasil)](dbusmenu.pt-BR.md)

# What crosses dbusmenu — and what doesn't

This document exists because five bugs in this project had the same cause, and I
treated each one as a separate problem before finding it.

## The cause

`libappindicator3` links `libdbusmenu-gtk3`:

```
$ ldd /usr/lib/x86_64-linux-gnu/libappindicator3.so.1 | grep dbusmenu
libdbusmenu-gtk3.so.4 => /lib/x86_64-linux-gnu/libdbusmenu-gtk3.so.4
libdbusmenu-glib.so.4 => /lib/x86_64-linux-gnu/libdbusmenu-glib.so.4
```

**The menu is not drawn by GTK on the user's machine.** It is serialized over
D-Bus and rendered by the *shell*. The program is the server; whoever draws it is
another process, possibly with another toolkit.

Only the properties the protocol defines get through:

```
label · enabled · visible · icon-name · icon-data
toggle-type · toggle-state · children-display
shortcut · disposition · accessible-desc
```

## What does NOT cross

No widget at all. These were tried and failed, all for the same reason:

| Attempt | Result |
|---|---|
| Nested `Gtk.Box` with title, bar and detail | whole row invisible |
| Right-aligned `Gtk.Label` inside a box | invisible |
| `Gtk.ProgressBar` inside a box | invisible |
| `Gtk.ProgressBar` as a direct child, insensitive | invisible |
| `Gtk.ProgressBar` as a direct child, sensitive | invisible |
| `Gtk.Image` as a child of `Gtk.MenuItem` | invisible |

Trying another arrangement doesn't help. The rule that remains: **each item is a
`Gtk.Label`, and what you see is its text.**

That's why the progress bar is drawn with characters, not with
`Gtk.ProgressBar`. It isn't an aesthetic choice.

## What crosses, and how

**Icon** — yes, but through the property, not the widget. The bridge reads the
`image` property of a **`Gtk.ImageMenuItem`** (`gtk_image_menu_item_get_type`
shows up in the `libdbusmenu-gtk3` symbols) and translates it to the protocol's
`icon-name`.

`ImageMenuItem` is deprecated in GTK 3 and emits a warning — but it's the only
widget the bridge recognizes, and the target here is the protocol, not GTK.

**Submenu** — yes, via `children-display`. It's the only way to group actions.

**Pango markup** — it's interpreted **locally** and only the resulting text is
sent. So `<b>` and `<span foreground>` don't reach the other side: bold, color
and size **don't exist** in this menu.

Practical consequence: visual hierarchy comes from indentation, symbols and
separators. And status color comes from **emoji**, which are glyphs colored by
the font, not text colored by the theme.

## Tooltips don't exist

```
$ strings libdbusmenu-glib.so.4 libdbusmenu-gtk3.so.4 | grep -ci tooltip
0
```

It isn't an implementation limitation, nor GNOME's: the protocol has no such
concept. Information you'd want on *hover* has to be in the label — that's why
the actionable sections announce "CLICK TO SCAN" in the title itself.

## `disposition` exists, but is unreachable from here

The protocol defines `normal / informative / warning / alert`, which would be
semantic emphasis without relying on manual color. The symbols exist in the
library:

```
genericmenuitem_set_disposition
genericmenuitem_get_disposition
```

But they're on the **client** side — used when the library *receives* a menu and
builds widgets. We're the server: we build a `GtkMenu` and the bridge converts
it. There's no GTK API from which it could derive `disposition`.

Whoever wants to use it has to speak dbusmenu directly, without the GTK bridge.
The migration to [`ksni`](https://crates.io/crates/ksni) described in the
[ROADMAP](../ROADMAP.md) could do that.

## Why this is documented

Each of the five bugs above got, on the spot, a plausible and wrong explanation
— width negotiation, insensitive dimming, dark theme. The explanations were
reasonable and none was the cause.

The decisive evidence was visible all along and went unnoticed: **the icons of
the action items didn't show up either**. Two kinds of widget failing at the same
time pointed to a boundary, not to two bugs.
