---
name: Bug
about: Algo não funciona como descrito
labels: bug
---

## O que aconteceu

## O que eu esperava

## Ambiente

Cole a saída destes três comandos — eles respondem quase todas as perguntas que
eu faria depois:

```sh
python3 -m clamav_tray --dump
systemctl list-units --all 'clam*'
echo "$XDG_CURRENT_DESKTOP $XDG_SESSION_TYPE"; gnome-shell --version 2>/dev/null
```

## Se for sobre o menu

Antes de abrir, veja [docs/dbusmenu.md](../../docs/dbusmenu.md): o menu é
renderizado pelo *shell*, não pelo GTK, e várias coisas não atravessam esse
protocolo — negrito, cor de texto e tooltip, entre outras. Pode ser limitação
conhecida em vez de bug.
