"""Frases voltadas ao usuario.

Separado de scan.py de proposito. O scan.py e o modulo 1 da migracao para Rust e
precisa continuar PURO — sem idioma, sem apresentacao, so texto entrando e struct
saindo. Traducao e decisao de interface, e interface muda junto com a camada
grafica, nao junto com a logica.

Consequencia pratica: quando o scan.rs existir, ele nao precisa saber que o
portugues existe.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .i18n import _
from .scan import ScanResult, Verdict, human_duration


def describe(result: ScanResult) -> str:
    """Uma linha sobre a ultima varredura. Sem icone: quem decide cor e o tray."""
    if result.verdict is Verdict.UNKNOWN:
        return _("no result recorded")
    if result.verdict is Verdict.ERROR:
        return _("scan did not finish")

    if result.verdict is Verdict.INFECTED:
        n = result.infected
        key = "{n} threat found" if n == 1 else "{n} threats found"
        return _(key, n=n)

    out = _("clean")
    if result.duration_secs is not None:
        out += f" ({human_duration(result.duration_secs)})"
    if result.unreadable:
        n = result.unreadable
        key = "{n} unreadable file" if n == 1 else "{n} unreadable files"
        out += ", " + _(key, n=n)
    return out


def relative_time(when: datetime) -> str:
    """'today 07:42' / 'tomorrow 03:01' / '23/09 03:00'.

    Data absoluta so quando hoje/ontem/amanha nao resolve — quem olha a bandeja
    quer saber se ja rodou hoje, nao a data.
    """
    local = when.astimezone()
    today = datetime.now(timezone.utc).astimezone().date()
    delta = (local.date() - today).days
    if prefix := {0: "today", -1: "yesterday", 1: "tomorrow"}.get(delta):
        return f"{_(prefix)} {local:%H:%M}"
    return f"{local:%d/%m %H:%M}"
