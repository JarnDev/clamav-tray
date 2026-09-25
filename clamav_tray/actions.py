"""Acoes do menu, sem amarrar a um desktop.

Modulo 4 da migracao. Pequeno, mas e o que decide se o programa serve fora do
GNOME.

O script que deu origem a isto chamava `gnome-terminal` e `nautilus` pelo nome, e
rodava `clamscan` na varredura sob demanda. Os tres estao corrigidos aqui:

- abrir pasta -> xdg-open, que todo desktop respeita
- terminal    -> detectado numa lista, com x-terminal-emulator primeiro
- varredura   -> clamdscan --fdpass quando ha socket; clamscan so como ultimo
                 recurso. Isso importa: clamscan recarrega ~1 GB de assinaturas a
                 cada execucao e varre em thread unica. Numa maquina com clamd ja
                 no ar, usa-lo e pagar duas vezes pela mesma base e saturar o disco.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Ordem deliberada: o alternatives do Debian primeiro, a proposta freedesktop
# depois, e so entao emuladores concretos.
TERMINALS = [
    "x-terminal-emulator", "xdg-terminal-exec",
    "kgx", "gnome-terminal", "konsole", "xfce4-terminal", "mate-terminal",
    "kitty", "alacritty", "wezterm", "foot", "xterm",
]

# Emuladores que exigem -e em vez de --.
_DASH_E = {"konsole", "xfce4-terminal", "mate-terminal", "xterm", "x-terminal-emulator"}


def open_path(path: Path) -> bool:
    """Abre pasta ou arquivo no gerenciador padrao."""
    if not shutil.which("xdg-open"):
        return False
    return _spawn(["xdg-open", str(path)])


def find_terminal(preferred: str | None = None) -> str | None:
    for name in ([preferred] if preferred else []) + TERMINALS:
        if name and (found := shutil.which(name)):
            return found
    return None


def run_in_terminal(command: str, preferred: str | None = None) -> bool:
    """Roda um comando de shell numa janela de terminal, que fica aberta no fim."""
    term = find_terminal(preferred)
    if not term:
        return False
    base = os.path.basename(term)
    sep = "-e" if base in _DASH_E else "--"
    held = f"{command}; printf '\\n[enter para fechar] '; read _"
    return _spawn([term, sep, "sh", "-c", held])


def scan_command(target: Path, socket: Path | None, quarantine: Path | None) -> str:
    """Monta a varredura sob demanda, preferindo o daemon."""
    if socket and socket.exists() and shutil.which("clamdscan"):
        argv = ["clamdscan", "--fdpass", "-i"]
    else:
        argv = ["clamscan", "-r", "-i"]
    if quarantine:
        argv.append(f"--move={_quote(str(quarantine))}")
    argv.append(_quote(str(target)))
    return " ".join(argv)


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _spawn(argv: list[str]) -> bool:
    """Dispara e esquece. O tray nao pode bloquear esperando o filho."""
    try:
        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False
