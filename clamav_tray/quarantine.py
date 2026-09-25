"""Estatisticas de quarentena — inclusive as que este processo nao consegue ler.

Ha duas quarentenas, com donos diferentes:

- a do SISTEMA, onde a varredura agendada (root) move. Tipicamente `750 root`, e
  isso esta certo: e malware guardado. Um processo de usuario nao consegue nem
  contar quantos arquivos ha la dentro.

- a do USUARIO, onde a varredura sob demanda move. Essa nos lemos direto.

Para a primeira existe uma CONVENCAO, nao uma dependencia: quem tem privilegio
publica um resumo legivel, e o tray le. Sem o arquivo, o tray diz que precisa de
root — nunca inventa zero.

O arquivo carrega o INSTANTE DA COLETA de proposito. Numero velho apresentado como
atual e pior que numero ausente: e exatamente assim que seis arquivos de trava do
clamdscan viraram "6 ameacas" no menu antes de eu perceber.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STATS_NAME = "quarantine.stats"
STATS_DIRS = (
    Path("/var/lib/clamav-tray"),
    Path("/run/clamav-tray"),
    Path("/var/lib/clamav"),
)

_LINE = re.compile(r"^\s*(\w+)\s*=\s*(.*?)\s*$")


@dataclass(frozen=True)
class Stats:
    count: int
    bytes: int = 0
    newest: datetime | None = None
    checked_at: datetime | None = None
    source: Path | None = None

    @property
    def age_secs(self) -> int | None:
        if self.checked_at is None:
            return None
        return int((datetime.now(timezone.utc) - self.checked_at).total_seconds())


def read_stats(extra: Path | None = None) -> Stats | None:
    """Le o resumo publicado por quem tem privilegio.

    Procura nos diretorios de estado usuais. Ausencia nao e erro: significa que
    ninguem aderiu a convencao nesta maquina.
    """
    candidates = [d / STATS_NAME for d in STATS_DIRS]
    if extra is not None:
        candidates.insert(0, extra if extra.name == STATS_NAME else extra / STATS_NAME)

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fields = {}
        for line in text.splitlines():
            if m := _LINE.match(line):
                fields[m.group(1).lower()] = m.group(2)
        if "count" not in fields:
            continue
        try:
            count = int(fields["count"])
        except ValueError:
            continue
        return Stats(
            count=count,
            bytes=_int(fields.get("bytes")),
            newest=_ts(fields.get("newest")),
            checked_at=_ts(fields.get("checked")) or _mtime(path),
            source=Path(fields["path"]) if fields.get("path") else None,
        )
    return None


def human_bytes(n: int) -> str:
    """2178432 -> 2,1 MB. Sem casa decimal abaixo de MB: "1,0 KB" e ruido."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n // 1024} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB".replace(".", ",")
    return f"{n / 1024 ** 3:.1f} GB".replace(".", ",")


def _int(value: str | None) -> int:
    try:
        return int(value) if value else 0
    except ValueError:
        return 0


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def _mtime(path: Path) -> datetime | None:
    """Ultimo recurso para a idade do dado: quando o arquivo foi escrito."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None
