"""Ponto de entrada. `python -m clamav_tray` ou o script `clamav-tray`."""
from __future__ import annotations

import sys


def main() -> int:
    from . import config

    cfg = config.load()

    from . import i18n
    i18n.set_language(cfg.language)

    if "--dump" in sys.argv:
        # Diagnostico sem GUI: mostra exatamente o que o tray veria. E tambem o
        # embriao do `clamav-status --json` que a trilha de Rust vai produzir.
        from . import history, scan, text, units

        ids = cfg.units or units.discover()
        state = units.query(ids)
        for unit in sorted(state.values(), key=lambda u: u.id):
            extra = f"  ha {scan.human_duration(unit.elapsed_secs)}" if unit.is_running_job and unit.elapsed_secs else ""
            print(f"{unit.id:34} {unit.kind.value:7} {unit.active_state:10} {unit.sub_state:10}{extra}")
        job = next((u.id for u in state.values() if u.kind is units.Kind.JOB), None)
        result = scan.parse_summary(history.last_summary(cfg.scan_log, job) or "")
        print(f"\nultima varredura: {text.describe(result)}  [{result.verdict.value}]")
        print(f"scan_log: {cfg.scan_log}   daemon_log: {cfg.log_file}   socket: {cfg.socket}")
        return 0

    try:
        from .tray import Tray
    except RuntimeError as err:
        print(f"clamav-tray: {err}", file=sys.stderr)
        return 1

    try:
        Tray(cfg).run()
    except RuntimeError as err:
        print(f"clamav-tray: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
