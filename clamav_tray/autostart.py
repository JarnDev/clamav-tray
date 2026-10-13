"""Faz o indicador subir sozinho no login. NAO precisa de root.

    clamav-tray --show-autostart [--xdg]        mostra o que seria gravado; nao grava
    clamav-tray --install-autostart [--xdg]     mostra, pede confirmacao, grava
    clamav-tray --uninstall-autostart [--xdg]   mostra o que sera removido, pede, remove

Duas formas, e a diferenca importa:

    systemd (padrao)  o processo e supervisionado: se morrer, volta. O journal
                      guarda o motivo.
    --xdg             autostart XDG: dispara e esquece. Se o processo morrer, o
                      icone some e nada registra o que houve — foi exatamente o
                      que aconteceu com o indicador que deu origem a este projeto.

INSPECIONAR ANTES DE GRAVAR. Um programa que se registra para rodar a cada login
pede confianca. Nada e gravado sem que o conteudo exato e o destino tenham sido
mostrados antes, e sem um "s" de quem esta no terminal; fora de terminal, so com
--yes explicito. Se ja existe arquivo no destino, o que se mostra e a DIFERENCA.

Antes este codigo era o packaging/install-autostart.sh, que nao ia no pacote do
PyPI: quem instalava por pipx precisava clonar o repositorio so para isso. O
script continua existindo e agora so chama este modulo.
"""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

UNIT_NAME = "clamav-tray.service"
DESKTOP_NAME = "clamav-tray.desktop"


@dataclass(frozen=True)
class Plan:
    mode: str               # "systemd" | "xdg"
    dest: Path
    content: str
    exec_line: str
    from_source: bool


def config_home() -> Path:
    # O systemd de usuario tambem honra XDG_CONFIG_HOME para ~/.config/systemd/user.
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def resolve_exec() -> tuple[str, Path | None]:
    """COMO o programa sera executado no login: (linha de comando, diretorio).

    O script antigo apontava a unidade para ~/.local/bin/clamav-tray mesmo
    rodando do codigo-fonte, onde esse arquivo nao existe: o servico entrava em
    laco com status=203/EXEC e o instalador dizia "Ativado". Agora resolve antes.
    """
    # absolute() e nao resolve(): o pipx poe em ~/.local/bin um LINK para dentro
    # do venv. O link e o caminho estavel; o alvo muda se o venv for recriado.
    if found := shutil.which("clamav-tray"):
        return str(Path(found).absolute()), None
    # Instalado por pipx mas fora do PATH desta shell: o proprio executavel.
    argv0 = Path(sys.argv[0])
    if argv0.name == "clamav-tray" and argv0.is_file():
        return str(argv0.absolute()), None
    # Codigo-fonte: python -m, com o diretorio do projeto como trabalho.
    raiz = Path(__file__).resolve().parent.parent
    return f"{sys.executable} -m clamav_tray", raiz


def render(mode: str, exec_line: str, workdir: Path | None) -> str:
    """Conteudo final do arquivo, a partir do modelo empacotado. Funcao pura."""
    if mode == "systemd":
        out = []
        for line in files("clamav_tray").joinpath("data", UNIT_NAME).read_text().splitlines():
            if line.startswith("ExecStart="):
                line = f"ExecStart={exec_line}"
            out.append(line)
            if line == "[Service]" and workdir:
                out.append(f"WorkingDirectory={workdir}")
        return "\n".join(out) + "\n"
    if mode == "xdg":
        modelo = files("clamav_tray").joinpath("data", DESKTOP_NAME).read_text().splitlines()
        return "\n".join(f"Exec={exec_line}" if l.startswith("Exec=") else l for l in modelo) + "\n"
    raise ValueError(mode)


def plan(mode: str) -> Plan:
    exec_line, workdir = resolve_exec()
    dest = (config_home() / "systemd" / "user" / UNIT_NAME if mode == "systemd"
            else config_home() / "autostart" / DESKTOP_NAME)
    return Plan(mode, dest, render(mode, exec_line, workdir), exec_line, workdir is not None)


def describe(p: Plan) -> str:
    """O que --show-autostart imprime, e o que --install-autostart mostra antes de perguntar."""
    linhas = [f"modo:     {p.mode}" + ("  (supervisionado pelo systemd)" if p.mode == "systemd"
                                       else "  (sem supervisao — prefira o modo systemd)"),
              f"destino:  {p.dest}",
              f"executa:  {p.exec_line}"]
    if p.from_source:
        linhas.append("          (clamav-tray nao esta no PATH: usando o codigo-fonte deste diretorio)")
    if p.dest.exists():
        atual = p.dest.read_text()
        if atual == p.content:
            linhas += ["", "O arquivo instalado ja e identico a este. Nada mudaria."]
        else:
            linhas += ["", "JA EXISTE um arquivo no destino. Diferenca (- atual, + novo):", ""]
            linhas += [l.rstrip("\n") for l in difflib.unified_diff(
                atual.splitlines(True), p.content.splitlines(True),
                fromfile=f"{p.dest} (atual)", tofile=f"{p.dest} (novo)")]
    else:
        linhas += ["", "Conteudo que seria gravado:", ""] + ["  " + l for l in p.content.splitlines()]
    if p.mode == "systemd":
        linhas += ["", "Depois de gravar, seriam executados (sem root):",
                   "  systemctl --user daemon-reload",
                   f"  systemctl --user enable --now {UNIT_NAME}"]
    return "\n".join(linhas)


def _confirm(pergunta: str, yes: bool) -> bool:
    if yes:
        return True
    if not sys.stdin.isatty():
        print("Sem terminal para confirmar. Inspecione com --show-autostart e repita com --yes.",
              file=sys.stderr)
        return False
    return input(f"{pergunta} [s/N] ").strip().lower() in ("s", "sim", "y", "yes")


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def show(mode: str) -> int:
    print(describe(plan(mode)))
    print("\nNada foi gravado. Para instalar: clamav-tray --install-autostart"
          + (" --xdg" if mode == "xdg" else ""))
    return 0


def install(mode: str, yes: bool = False) -> int:
    p = plan(mode)
    print(describe(p))
    print()
    if not _confirm("Gravar e ativar?", yes):
        print("Cancelado. Nada foi gravado.")
        return 1
    p.dest.parent.mkdir(parents=True, exist_ok=True)
    p.dest.write_text(p.content)
    p.dest.chmod(0o644)
    if mode == "xdg":
        print(f"Gravado: {p.dest}")
        print("Desinstalar: clamav-tray --uninstall-autostart --xdg")
        return 0
    _systemctl("daemon-reload")
    r = _systemctl("enable", "--now", UNIT_NAME)
    if r.returncode != 0:
        print(f"FALHOU ao habilitar: {r.stderr.strip()}", file=sys.stderr)
        return 1
    # CONFERE em vez de afirmar: a versao anterior dizia "Ativado" enquanto o
    # servico falhava em laco. Dois segundos bastam para um 203/EXEC aparecer.
    time.sleep(2)
    if _systemctl("is-active", "--quiet", UNIT_NAME).returncode != 0:
        print("FALHOU ao iniciar:", file=sys.stderr)
        print(_systemctl("status", UNIT_NAME, "--no-pager").stdout[:1500], file=sys.stderr)
        return 1
    print("Ativado e rodando.")
    print("Desinstalar: clamav-tray --uninstall-autostart")
    return 0


def uninstall(mode: str, yes: bool = False) -> int:
    p = plan(mode)
    if not p.dest.exists():
        print(f"Nada instalado em {p.dest}.")
        return 0
    print(f"Seria removido: {p.dest}")
    if mode == "systemd":
        print(f"Antes: systemctl --user disable --now {UNIT_NAME}")
    print()
    if not _confirm("Remover?", yes):
        print("Cancelado. Nada foi removido.")
        return 1
    if mode == "systemd":
        _systemctl("disable", "--now", UNIT_NAME)
    p.dest.unlink()
    if mode == "systemd":
        _systemctl("daemon-reload")
    print(f"Removido: {p.dest}")
    return 0


def main(argv: list[str]) -> int | None:
    """Despacha se algum comando de autostart estiver em argv; senao, None."""
    mode = "xdg" if "--xdg" in argv else "systemd"
    yes = "--yes" in argv
    if "--show-autostart" in argv:
        return show(mode)
    if "--install-autostart" in argv:
        return install(mode, yes)
    if "--uninstall-autostart" in argv:
        return uninstall(mode, yes)
    return None
