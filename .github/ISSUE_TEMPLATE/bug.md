---
name: Bug
about: Something does not work as documented
labels: bug
---

## What happened

## What I expected

## Environment

Paste the output of these three commands — they answer almost every question I
would ask next:

```sh
python3 -m clamav_tray --dump
systemctl list-units --all 'clam*'
echo "$XDG_CURRENT_DESKTOP $XDG_SESSION_TYPE"; gnome-shell --version 2>/dev/null
```

## If it is about the menu

Before opening, see [docs/dbusmenu.md](../../docs/dbusmenu.md): the menu is
rendered by the *shell*, not by GTK, and several things do not cross that
protocol — bold, text color and tooltips, among others. It may be a known
limitation rather than a bug.

<!-- Português é bem-vindo. -->
