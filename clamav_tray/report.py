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

from datetime import datetime

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
    if any(not u.is_healthy for u in state.values()):
        return "warn"
    return "ok"


def build(
    cfg: Config,
    state: dict[str, Unit],
    job: Unit | None,
    result: ScanResult,
    loose_scan: bool = False,
    version: str | None = None,
) -> dict:
    return {
        "schema": SCHEMA,
        "version": version,
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
        },
        "paths": {
            "socket": _path(cfg.socket),
            "scan_log": _path(cfg.scan_log),
            "daemon_log": _path(cfg.log_file),
            "quarantine": _path(cfg.quarantine),
            "user_quarantine": _path(cfg.user_quarantine),
        },
    }
