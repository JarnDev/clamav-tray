"""O estado que o tray enxerga, como dado: `clamav-tray --dump --json`.

E um CONTRATO, documentado em docs/json.md. Script, Glance, Conky e o futuro
`clamav-status` em Rust leem isto; mudar um campo quebra quem le. Por isso:

- `schema` sobe quando um campo muda de sentido ou some. Campo NOVO nao sobe.
- Ausencia e `null`, nunca omissao: quem le nao precisa distinguir "nao veio"
  de "nao existe".
- Horarios em ISO 8601 com fuso. Sem fuso, um script em outra maquina erraria
  a hora sem perceber.

A montagem e uma funcao pura — estado entra, dicionario sai — para ser testada
sem systemd rodando, como o scan.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import i18n, progress as progress_mod
from .config import Config
from .scan import ScanResult
from .units import Unit

SCHEMA = 1


def _ts(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _path(value) -> str | None:
    return str(value) if value else None


def status(state: dict[str, Unit], result: ScanResult, loose_scan: bool = False) -> str:
    """Mesma precedencia do icone: ameaca > varrendo > servico caido > ok.

    Midia removivel pendente fica de fora: "pendente" depende do que o tray ja
    varreu NESTA sessao, que esta na memoria dele e nao no sistema.
    """
    if result.is_alarming:
        return "threat"
    if loose_scan or any(u.is_running_job for u in state.values()):
        return "busy"
    # Sem unidade nenhuma, "ok" afirmaria protecao que nao existe — visto num
    # Fedora recem-instalado, onde nada vem habilitado.
    if not state or any(not u.is_healthy for u in state.values()):
        return "warn"
    return "ok"


def state_path() -> Path:
    """Onde o tray publica o estado a cada atualizacao (tmpfs, some no logout)."""
    return progress_mod.runtime_dir() / "state.json"


def version() -> str:
    from . import __version__
    return __version__


def to_json(d: dict) -> str:
    return json.dumps(d, indent=2, ensure_ascii=False)


def quarantine_info(cfg: Config) -> dict:
    """As duas quarentenas. `null` quando nao da para saber — nao e zero: a do
    sistema e de root e so se conhece pelo resumo que alguem com privilegio publica."""
    from . import config as config_mod, quarantine
    stats = quarantine.read_stats()
    user_n = config_mod.quarantine_count(cfg.user_quarantine) if cfg.user_quarantine else None
    return {
        "system": None if stats is None else {
            "count": stats.count, "bytes": stats.bytes, "checked_at": _ts(stats.checked_at)},
        "user": None if user_n is None else {"count": user_n},
    }


def _media(media, scanned) -> list:
    out = []
    for dev in media or []:
        reg = (scanned or {}).get(dev.key)
        out.append({
            "key": dev.key,
            "label": dev.label,
            "mountpoint": str(dev.mountpoint),
            "size_bytes": dev.size_bytes,
            # O que o tray varreu NESTA sessao. null = nao varrida (ou --dump, que
            # nao tem como saber: isso vive na memoria do tray).
            "scanned": None if reg is None else {
                "at": _ts(reg[0]), "infected": reg[1], "not_contained": reg[2]},
        })
    return out


def build(
    cfg: Config,
    state: dict[str, Unit],
    job: Unit | None,
    result: ScanResult,
    loose_scan: bool = False,
    version: str | None = None,
    *,
    progress=None,
    media=None,
    media_scanned: dict | None = None,
    quarantine: dict | None = None,
    producer: str = "dump",
    now: datetime | None = None,
) -> dict:
    return {
        "schema": SCHEMA,
        "version": version,
        # Quem gerou e quando: o leitor do state.json precisa saber se o tray
        # ainda esta vivo — arquivo velho e tray parado.
        "producer": producer,
        # Idioma resolvido da interface, para quem desenha falar a mesma lingua.
        "language": i18n.current(),
        # Fuso local e segundos inteiros, como os demais horarios do documento.
        "generated_at": _ts(now or datetime.now(timezone.utc).astimezone().replace(microsecond=0)),
        # Intervalo entre atualizacoes: quem le o state.json mede "velho" por ele,
        # e nao por um numero fixo que quebraria com refresh_secs alterado.
        "refresh_secs": cfg.refresh_secs,
        "status": status(state, result, loose_scan),
        "units": [
            {
                "id": u.id,
                "label": cfg.label_for(u.id),
                "kind": u.kind.value,
                "user_scope": u.user_scope,
                "active_state": u.active_state,
                "sub_state": u.sub_state,
                "result": u.result,
                "healthy": u.is_healthy,
                "running": u.is_running_job,
                "exit_status": u.exit_status,
                "started_at": _ts(u.started_at),
                "finished_at": _ts(u.finished_at),
                "next_run": _ts(u.next_elapse),
            }
            for u in sorted(state.values(), key=lambda u: u.id)
        ],
        "scan": {
            # A unidade de onde veio o resultado abaixo — a mesma que o tray escolhe.
            "unit": job.id if job else None,
            "running": bool(job and job.is_running_job) or loose_scan,
            "outside_systemd": loose_scan,
            "verdict": result.verdict.value,
            "infected": result.infected,
            "unreadable": result.unreadable,
            "scanned": result.scanned,
            "duration_secs": result.duration_secs,
            "finished_at": _ts(job.finished_at) if job else None,
            "progress": None if progress is None else {
                "done": progress.done, "total": progress.total},
        },
        "media": _media(media, media_scanned),
        "quarantine": quarantine,
        "paths": {
            "socket": _path(cfg.socket),
            "scan_log": _path(cfg.scan_log),
            "daemon_log": _path(cfg.log_file),
            "quarantine": _path(cfg.quarantine),
            "user_quarantine": _path(cfg.user_quarantine),
        },
    }
