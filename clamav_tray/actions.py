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


TRANSIENT_UNIT = "clamav-tray-scan"


def scan_argv(target: Path, socket: Path | None, quarantine: Path | None) -> list[str]:
    """Varredura sob demanda, preferindo o daemon.

    clamscan recarrega ~1 GB de assinaturas a cada execucao e varre em thread
    unica; com o clamd no ar, usa-lo e pagar duas vezes pela mesma base.
    """
    if socket and socket.exists() and shutil.which("clamdscan"):
        argv = ["clamdscan", "--fdpass", "-i"]
    else:
        argv = ["clamscan", "-r", "-i"]
    if quarantine:
        argv.append(f"--move={quarantine}")
    argv.append(str(target))
    return argv


def start_scan(target: Path, socket: Path | None, quarantine: Path | None) -> bool:
    """Lanca a varredura como UNIDADE TRANSITORIA do usuario.

    Por que nao um comando solto num terminal, como era antes: o indicador observa
    unidades. Processo solto e invisivel para ele — nem "em andamento" aparecia,
    nem o resultado era capturado, porque a saida ia para a tela e nao para lugar
    nenhum que desse para reler.

    Como unidade, o systemd registra inicio, fim e resultado, e o SCAN SUMMARY vai
    para o journal do usuario, de onde o modulo history ja sabe ler.

    Sem systemd-run, cai no terminal — pior, mas melhor que nao varrer.
    """
    argv = scan_argv(target, socket, quarantine)
    if not shutil.which("systemd-run"):
        return run_in_terminal(" ".join(_quote(a) for a in argv))

    # Nome FIXO, nao com timestamp: o indicador precisa saber onde olhar. Com nome
    # sorteado a cada execucao ele nunca reencontraria a unidade.
    #
    # --remain-after-exit faz a unidade PERMANECER depois de terminar, carregando
    # inicio, fim e resultado. Sem isso ela some no instante em que acaba e o
    # resultado se perde — medido: a varredura rodou, o SCAN SUMMARY foi para o
    # journal, e a unidade ja nao existia 3s depois.
    subprocess.run(
        ["systemctl", "--user", "reset-failed", f"{TRANSIENT_UNIT}.service"],
        capture_output=True, timeout=10, check=False,
    )
    subprocess.run(
        ["systemctl", "--user", "stop", f"{TRANSIENT_UNIT}.service"],
        capture_output=True, timeout=10, check=False,
    )
    return _spawn([
        "systemd-run", "--user", "--quiet",
        f"--unit={TRANSIENT_UNIT}",
        "--remain-after-exit",
        "--description=ClamAV on-demand scan (clamav-tray)",
        *argv,
    ])


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


def list_quarantine(path: Path, terminal: str | None = None) -> bool:
    """Lista a quarentena num TERMINAL, nunca num gerenciador de arquivos.

    Duas razoes, ambas praticas:

    1. A quarentena costuma ser `750` dono root — abrir com xdg-open daria
       "permission denied" numa janela, sem explicar nada. No terminal o sudo
       pergunta a senha e a pessoa entende o que esta acontecendo.

    2. Ali dentro ha MALWARE de verdade. Gerenciador de arquivos gera miniatura,
       indexa e le cabecalho dos arquivos que mostra — encostar num executavel
       malicioso com o thumbnailer e um jeito ruim de olhar para ele. `ls` nao
       abre nada.
    """
    return run_in_terminal(f"sudo ls -la {_quote(str(path))}", terminal)
