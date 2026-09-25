"""Progresso real de uma varredura em curso.

Nao e estimativa por tempo: e contagem. Com `--file-list`, o clamdscan imprime UMA
LINHA POR ARQUIVO, mesmo sem `-v`. Entao:

    progresso = linhas impressas / linhas da lista

Duas fontes, porque as duas varreduras tem donos diferentes:

1. A varredura SOB DEMANDA e nossa: sabemos onde a lista e a saida estao.

2. A AGENDADA roda como root e manda a saida para um arquivo temporario com nome
   aleatorio. Espiar pelo `/proc/<pid>/fd/1` dela nao funciona — verificado:
   "Permission denied". Um indicador de usuario nao ve dentro de um processo de
   root, e essa fronteira esta certa.

   Para essa existe uma CONVENCAO, nao uma dependencia: se houver um arquivo de
   contador legivel, o tray usa. Sem ele, cai no tempo decorrido. Qualquer script
   de varredura pode aderir escrevendo uma linha.

A contagem e INCREMENTAL. Reler um arquivo de saida com um milhao de linhas a cada
atualizacao custaria mais que a propria varredura; aqui so os bytes novos desde a
ultima leitura sao percorridos.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# Convencao: um arquivo com "feitos/total" numa linha. Ver README.
COUNTER_NAMES = ("scan.progress", "clamav-scan.progress")

_COUNTER = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


@dataclass(frozen=True)
class Progress:
    done: int
    total: int

    @property
    def fraction(self) -> float | None:
        if self.total <= 0:
            return None
        return min(self.done / self.total, 1.0)

    @property
    def percent(self) -> int:
        f = self.fraction
        return int(f * 100) if f is not None else 0


def runtime_dir() -> Path:
    """Onde a varredura sob demanda deixa lista e saida.

    XDG_RUNTIME_DIR e tmpfs e some no logout, que e exatamente a vida util destes
    arquivos — eles nao sobrevivem a sessao nem devem.
    """
    base = os.environ.get("XDG_RUNTIME_DIR")
    path = Path(base) if base else Path("/tmp")
    return path / "clamav-tray"


def list_path() -> Path:
    return runtime_dir() / "scan.list"


def output_path() -> Path:
    return runtime_dir() / "scan.out"


def from_counter_file(directory: Path | None) -> Progress | None:
    """Le o contador que um script de varredura tenha publicado."""
    if directory is None:
        return None
    for name in COUNTER_NAMES:
        path = directory / name
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if m := _COUNTER.match(text.splitlines()[0] if text else ""):
            return Progress(done=int(m.group(1)), total=int(m.group(2)))
    return None


def count_lines(path: Path) -> int:
    """Contagem simples, para arquivos pequenos como a lista."""
    try:
        with path.open("rb") as fh:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: fh.read(1 << 20), b""))
    except OSError:
        return 0


class LineCounter:
    """Conta linhas de um arquivo que CRESCE, lendo so o que chegou.

    Guarda deslocamento e total. Se o arquivo encolher ou trocar de inode — uma
    varredura nova sobrescrevendo a anterior —, recomeca do zero em vez de
    devolver um numero que so faz sentido para o arquivo antigo.
    """

    def __init__(self, path: Path):
        self.path = path
        self._offset = 0
        self._lines = 0
        self._inode: int | None = None

    def count(self) -> int:
        try:
            stat = self.path.stat()
        except OSError:
            self._reset()
            return 0

        if self._inode != stat.st_ino or stat.st_size < self._offset:
            self._reset()
            self._inode = stat.st_ino

        if stat.st_size == self._offset:
            return self._lines

        try:
            with self.path.open("rb") as fh:
                fh.seek(self._offset)
                while chunk := fh.read(1 << 20):
                    self._lines += chunk.count(b"\n")
                self._offset = fh.tell()
        except OSError:
            return self._lines
        return self._lines

    def _reset(self) -> None:
        self._offset = 0
        self._lines = 0
        self._inode = None
