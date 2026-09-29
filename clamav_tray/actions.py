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


def can_quarantine(quarantine: Path | None) -> bool:
    """Se ESTE usuario consegue mover arquivo para a quarentena.

    Quase sempre False, e por bom motivo: a quarentena e `750` dono root. A
    varredura agendada roda como root e move; a sob demanda roda como voce e nao.
    """
    return bool(quarantine and os.access(quarantine, os.W_OK | os.X_OK))


def scan_argv(
    target: Path | None,
    socket: Path | None,
    quarantine: Path | None,
    file_list: Path | None = None,
) -> list[str]:
    """Varredura sob demanda, preferindo o daemon.

    clamscan recarrega ~1 GB de assinaturas a cada execucao e varre em thread
    unica; com o clamd no ar, usa-lo e pagar duas vezes pela mesma base.

    `--move` SO entra se o usuario puder escrever na quarentena. Passa-lo sem
    permissao nao degrada: o clamdscan ABORTA antes de varrer um unico arquivo,
    com "Failed to create quarantine lock file ... Permission denied" e status 2.
    Medido — a varredura de 771 MB terminou em 0,000s sem olhar nada.

    Sem `--move` a varredura vira DETECCAO: ela aponta o que achou e nao move nada.
    Quem move e a varredura agendada, que roda como root.
    """
    # `-i` (--infected) imprime SO os infectados. E o que se quer normalmente —
    # e o que torna o progresso impossivel de contar, porque a barra se apoia na
    # linha "arquivo: OK" de cada arquivo. Com lista, portanto, sem -i.
    #
    # Custo: a saida passa a ter uma linha por arquivo (~70 MB para 1,1 milhao).
    # Fica em tmpfs e some no logout; e lida uma vez, incrementalmente.
    quiet = [] if file_list is not None else ["-i"]
    if socket and socket.exists() and shutil.which("clamdscan"):
        argv = ["clamdscan", "--fdpass", *quiet]
    else:
        argv = ["clamscan", "-r", *quiet]
    if can_quarantine(quarantine):
        argv.append(f"--move={quarantine}")
    if file_list is not None:
        argv.append(f"--file-list={file_list}")
    else:
        argv.append(str(target))
    return argv


def stop_scan() -> bool:
    """Interrompe a varredura sob demanda."""
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", f"{TRANSIENT_UNIT}.service"],
            capture_output=True, timeout=15, check=False,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# Exclusoes padrao da varredura sob demanda. Nao existiam: ela varria os 221 GB
# inteiros, inclusive o que a varredura agendada ja pula. Volume enorme, risco
# desprezivel — binario de jogo assinado pela loja, cache de navegador, pacote
# gerenciado. O que NAO sai e onde o risco mora: Downloads, Documentos, codigo.
DEFAULT_EXCLUDES = [
    # A PROPRIA quarentena, antes de tudo: ela fica dentro da home, e sem esta
    # linha a varredura reencontraria o que ja foi isolado e moveria de novo —
    # para dentro de si mesma, ou para a quarentena de root se a varredura for
    # dela. A contagem do menu esvaziaria sozinha, sem explicacao.
    ".local/share/clamav-tray/quarantine",
    ".cache", ".local/share/Trash", ".local/share/Steam", ".local/share/lutris",
    ".local/share/pnpm", ".local/share/virtualenvs", ".local/share/pipx",
    ".config/google-chrome", ".mozilla/firefox",
]
# Por NOME, em qualquer profundidade — diferente das de cima, que sao caminhos
# fixos. Medido: excluir ".cache" so no topo deixava passar .cargo/registry/index/
# .cache, snap/*/common/.cache e varios outros. Cache e regeneravel onde quer que
# esteja.
EXCLUDE_NAMES = ["node_modules", ".venv", "venv", "__pycache__", ".cache"]


def build_file_list(target: Path, dest: Path, excludes: list[str] | None = None) -> int:
    """Monta a lista de arquivos a varrer e devolve quantos sao.

    POR QUE listar antes em vez de apontar o diretorio: com `--file-list` o
    clamdscan imprime UMA LINHA POR ARQUIVO, e e isso que torna a barra de
    progresso uma CONTAGEM em vez de um palpite pelo relogio. Apontando o
    diretorio ele imprime uma linha so, no fim.

    Custo medido: 4.500.726 arquivos listados em 10 segundos. Irrelevante diante de
    uma varredura de horas — e de brinde vem as exclusoes, que a varredura sob
    demanda nao tinha.

    Nomes com quebra de linha ficam de fora: o formato de lista e delimitado por
    linha, e um nome assim viraria dois caminhos inexistentes.
    """
    ex = DEFAULT_EXCLUDES if excludes is None else excludes
    argv = ["find", str(target)]
    if ex or EXCLUDE_NAMES:
        argv.append("(")
        parts: list[str] = []
        for rel in ex:
            parts += ["-path", str(target / rel), "-o"]
        for name in EXCLUDE_NAMES:
            parts += ["-name", name, "-o"]
        argv += parts[:-1]
        argv += [")", "-prune", "-o"]
    argv += ["-type", "f", "-print0"]

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return 0

    kept = [p for p in proc.stdout.split(b"\0") if p and b"\n" not in p]
    dest.write_bytes(b"\n".join(kept) + (b"\n" if kept else b""))
    return len(kept)


def start_scan(
    target: Path,
    socket: Path | None,
    quarantine: Path | None,
    excludes: list[str] | None = None,
) -> bool:
    """Lanca a varredura como UNIDADE TRANSITORIA do usuario.

    Por que nao um comando solto num terminal, como era antes: o indicador observa
    unidades. Processo solto e invisivel para ele — nem "em andamento" aparecia,
    nem o resultado era capturado, porque a saida ia para a tela e nao para lugar
    nenhum que desse para reler.

    Como unidade, o systemd registra inicio, fim e resultado, e o SCAN SUMMARY vai
    para o journal do usuario, de onde o modulo history ja sabe ler.

    Sem systemd-run, cai no terminal — pior, mas melhor que nao varrer.
    """
    # Lista propria: e o que permite contar o progresso e aplicar exclusoes.
    from . import progress
    listing = progress.list_path()
    out = progress.output_path()
    # ESVAZIA a saida antes de comecar. O `>` do shell la embaixo so trunca quando
    # o shell de fato roda; ate la — e para sempre, se o lancamento falhar — o
    # arquivo ainda guarda o resumo da varredura ANTERIOR, e quem le nao tem como
    # saber que e velho. Era metade do bug do alarme preso: o resultado de uma
    # varredura de quatro dias atras respondia por "agora".
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"")
    except OSError:
        pass
    # Midia removivel nao tem o que excluir: ali nao ha cache de navegador nem
    # node_modules. Passar `excludes=[]` evita aplicar as regras da home num
    # pendrive, onde elas so gastariam tempo.
    total = build_file_list(target, listing, excludes)
    if total:
        argv = scan_argv(None, socket, quarantine, file_list=listing)
    else:
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
    # A saida vai para ARQUIVO, nao para o journal: o progresso e contado nela, e
    # reler o journal a cada atualizacao sairia caro.
    shell = " ".join(_quote(a) for a in argv) + f" > {_quote(str(out))} 2>&1"
    return _spawn([
        "systemd-run", "--user", "--quiet",
        f"--unit={TRANSIENT_UNIT}",
        "--remain-after-exit",
        "--description=ClamAV on-demand scan (clamav-tray)",
        "/bin/sh", "-c", shell,
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


def list_quarantine(
    path: Path, terminal: str | None = None, privileged: bool = True
) -> bool:
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
    prefix = "sudo " if privileged else ""
    return run_in_terminal(f"{prefix}ls -la {_quote(str(path))}", terminal)
