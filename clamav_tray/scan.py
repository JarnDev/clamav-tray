"""Interpretacao do resultado de uma varredura.

Modulo 1 da migracao para Rust: funcoes PURAS, sem I/O e sem estado. Texto entra,
struct sai. Da para testar sem ClamAV instalado e sem systemd rodando.

A regra central deste arquivo: o veredito vem do SCAN SUMMARY, NAO do codigo de
saida da unidade. O clamdscan devolve 2 se QUALQUER arquivo nao pode ser aberto, e
numa varredura de horas sobre milhoes de arquivos e rotina que arquivos temporarios
desaparecam no meio do caminho. Tratar isso como falha faz o indicador gritar todo
dia por nada, e um alarme que sempre toca deixa de ser alarme.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    CLEAN = "clean"
    """Nenhum infectado. Pode haver arquivos ilegiveis — ver `unreadable`."""

    INFECTED = "infected"
    """Pelo menos um infectado. E o unico caso que merece alarme."""

    ERROR = "error"
    """A varredura nao chegou a produzir um resumo (abortou, daemon fora do ar)."""

    UNKNOWN = "unknown"
    """Nao havia resumo para ler. Nao e o mesmo que erro."""


@dataclass(frozen=True)
class ScanResult:
    verdict: Verdict
    infected: int = 0
    unreadable: int = 0
    """Arquivos que o scanner nao conseguiu abrir. Quase sempre transitorios."""
    scanned: int | None = None
    duration_secs: int | None = None

    @property
    def is_alarming(self) -> bool:
        """So infeccao e alarme. Arquivo ilegivel e ruido operacional."""
        return self.verdict is Verdict.INFECTED


# "Infected files: 0" / "Total errors: 6" / "Scanned files: 1099137"
_COUNT = re.compile(r"^(Infected files|Total errors|Scanned files):\s*(\d+)\s*$", re.M)

# "Time: 16317.863 sec (271 m 57 s)"
_TIME = re.compile(r"^Time:\s*([\d.]+)\s*sec", re.M)


def parse_summary(text: str) -> ScanResult:
    """Le o bloco SCAN SUMMARY que clamscan e clamdscan imprimem no fim.

    Aceita texto com lixo em volta (log acumulado, mensagens de ERROR antes do
    resumo). Se nao houver resumo, devolve UNKNOWN em vez de inventar zero — nao
    saber e diferente de estar limpo.
    """
    counts = {m.group(1): int(m.group(2)) for m in _COUNT.finditer(text)}
    if "Infected files" not in counts:
        return ScanResult(verdict=Verdict.UNKNOWN)

    infected = counts["Infected files"]
    duration = None
    if m := _TIME.search(text):
        duration = int(float(m.group(1)))

    return ScanResult(
        verdict=Verdict.INFECTED if infected else Verdict.CLEAN,
        infected=infected,
        unreadable=counts.get("Total errors", 0),
        scanned=counts.get("Scanned files"),
        duration_secs=duration,
    )


def describe(result: ScanResult) -> str:
    """Uma linha para o menu. Sem emoji: quem decide o icone e o tray."""
    if result.verdict is Verdict.UNKNOWN:
        return "sem resultado registrado"
    if result.verdict is Verdict.ERROR:
        return "a varredura nao concluiu"
    if result.verdict is Verdict.INFECTED:
        n = result.infected
        return f"{n} ameaca{'s' if n != 1 else ''} encontrada{'s' if n != 1 else ''}"

    out = "limpa"
    if result.duration_secs is not None:
        out += f" ({human_duration(result.duration_secs)})"
    if result.unreadable:
        n = result.unreadable
        out += f", {n} arquivo{'s' if n != 1 else ''} ilegive{'is' if n != 1 else 'l'}"
    return out


def human_duration(secs: int) -> str:
    """4h33 / 12m / 45s — sempre a unidade mais grossa que ainda informa."""
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}"
