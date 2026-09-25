"""Camada grafica: bandeja, menu, icone.

Modulo 5 e ULTIMO da migracao para Rust, de proposito. E onde mora o estado
compartilhado entre callbacks, e onde depurar e pior: quando a bandeja nao aparece,
nao ha mensagem de erro, so ausencia.

Duas bibliotecas de AppIndicator convivem no mundo e nenhuma esta em todo lugar:
o Ubuntu costuma trazer a antiga (AppIndicator3), Fedora e Arch tendem a Ayatana.
Tentamos as duas. Assumir uma quebra metade das distros.

A aparencia das linhas mora em widgets.py. Aqui fica so a decisao de QUAL linha
mostrar — que e a parte que sobrevive a reescrita.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

_INDICATOR = None
for _lib, _ver in (("AyatanaAppIndicator3", "0.1"), ("AppIndicator3", "0.1")):
    try:
        gi.require_version(_lib, _ver)
        _INDICATOR = __import__("gi.repository", fromlist=[_lib]).__dict__[_lib]
        break
    except (ValueError, ImportError, KeyError):
        continue

from . import actions, history, scan, units, widgets  # noqa: E402
from .config import Config  # noqa: E402
from .scan import Verdict  # noqa: E402

ICONS = {
    "ok": "security-high-symbolic",
    "busy": "security-medium-symbolic",
    "warn": "security-low-symbolic",
}

# Duracao tipica de uma varredura completa, so para dar forma a barra quando ha
# historico. Nao e previsao: o clamdscan nao informa progresso.
_FALLBACK_SCAN_SECS = 4 * 3600


class Tray:
    def __init__(self, cfg: Config):
        if _INDICATOR is None:
            raise RuntimeError(
                "nenhum AppIndicator encontrado — instale gir1.2-appindicator3-0.1 "
                "ou gir1.2-ayatanaappindicator3-0.1"
            )
        self.cfg = cfg
        self.unit_ids = cfg.units or units.discover()
        self._last_duration: int | None = None
        self.indicator = _INDICATOR.Indicator.new(
            "clamav-tray", ICONS["ok"], _INDICATOR.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(_INDICATOR.IndicatorStatus.ACTIVE)
        self.indicator.set_title("ClamAV")

    def run(self) -> None:
        self._refresh()
        GLib.timeout_add_seconds(self.cfg.refresh_secs, self._refresh)
        Gtk.main()

    # ---------------------------------------------------------------- estado

    def _refresh(self) -> bool:
        state = units.query(self.unit_ids)
        running = [u for u in state.values() if u.is_running_job]
        result = scan.parse_summary(
            history.last_summary(self.cfg.scan_log, self._scan_unit(state)) or ""
        )
        if result.duration_secs:
            self._last_duration = result.duration_secs

        # Precedencia: ameaca > varrendo > servico caido > ok. Uma infeccao nunca
        # pode ser escondida por uma varredura em andamento.
        broken = [u for u in state.values() if not u.is_healthy]
        if result.is_alarming:
            key, color = "warn", widgets.RED
        elif running:
            key, color = "busy", widgets.BLUE
        elif broken:
            key, color = "warn", widgets.AMBER
        else:
            key, color = "ok", widgets.GREEN

        self.indicator.set_icon_full(ICONS[key], "ClamAV")
        self.indicator.set_menu(
            self._build_menu(state, running, broken, result, color)
        )
        return True  # mantem o timer vivo

    def _scan_unit(self, state: dict[str, units.Unit]) -> str | None:
        for unit_id, unit in state.items():
            if unit.kind is units.Kind.JOB:
                return unit_id
        return None

    def _headline(self, running, broken, result) -> tuple[str, str]:
        if result.is_alarming:
            n = result.infected
            return ("Ameaça detectada", f"{n} arquivo(s) em quarentena")
        if running:
            return ("Varredura em andamento", "")
        if broken:
            nomes = ", ".join(self.cfg.label_for(u.id) for u in broken[:2])
            resto = f" e mais {len(broken) - 2}" if len(broken) > 2 else ""
            return ("Atenção", f"{nomes}{resto} com problema")
        return ("Protegido", "todos os serviços no ar")

    # ------------------------------------------------------------------ menu

    def _build_menu(self, state, running, broken, result, color) -> Gtk.Menu:
        menu = Gtk.Menu()
        menu.set_reserve_toggle_size(False)

        title, subtitle = self._headline(running, broken, result)
        menu.append(widgets.header(title, subtitle, color))
        menu.append(widgets.separator())

        # --- varredura ---------------------------------------------------
        menu.append(widgets.section("Varredura"))

        if running:
            job = running[0]
            elapsed = job.elapsed_secs or 0
            total = self._last_duration or _FALLBACK_SCAN_SECS
            menu.append(
                widgets.progress_row(
                    "Em andamento",
                    min(elapsed / total, 0.99) if total else None,
                    f"há {scan.human_duration(elapsed)}"
                    + (f" · estimativa {scan.human_duration(total)}" if self._last_duration else ""),
                )
            )
        else:
            menu.append(
                widgets.status_row(
                    "Última",
                    self._when_last(state),
                    widgets.RED if result.is_alarming else (
                        widgets.DIM if result.verdict is Verdict.UNKNOWN else widgets.GREEN
                    ),
                    scan.describe(result),
                )
            )

        if nxt := self._next_scan(state):
            menu.append(widgets.status_row("Próxima", nxt, widgets.DIM))

        # --- servicos ----------------------------------------------------
        menu.append(widgets.section("Serviços"))
        for unit in sorted(state.values(), key=lambda u: (u.kind.value, u.id)):
            if unit.kind is units.Kind.TIMER:
                continue
            if unit.is_running_job:
                continue  # ja apareceu na barra de progresso
            menu.append(
                widgets.status_row(
                    self.cfg.label_for(unit.id),
                    unit.sub_state,
                    widgets.GREEN if unit.is_healthy else widgets.AMBER,
                )
            )

        if not history.journal_readable() and self.cfg.scan_log is None:
            menu.append(
                widgets.status_row(
                    "Histórico", "indisponível", widgets.DIM,
                    "sem acesso ao journal (grupo adm ou systemd-journal)",
                )
            )

        # --- acoes -------------------------------------------------------
        menu.append(widgets.separator())
        menu.append(
            widgets.action("Varrer minha home agora", "media-playback-start-symbolic", self._on_scan)
        )
        if self.cfg.quarantine:
            menu.append(widgets.action("Abrir quarentena", "folder-symbolic", self._on_quarantine))
        if self.cfg.scan_log or self.cfg.log_file:
            menu.append(widgets.action("Ver logs", "text-x-generic-symbolic", self._on_logs))
        menu.append(widgets.separator())
        menu.append(widgets.action("Sair", "application-exit-symbolic", lambda _: Gtk.main_quit()))

        menu.show_all()
        return menu

    # ------------------------------------------------------------- formatos

    def _when_last(self, state) -> str:
        for unit in state.values():
            if unit.kind is units.Kind.JOB and unit.finished_at:
                return _relative(unit.finished_at)
        return "—"

    def _next_scan(self, state) -> str | None:
        for unit in state.values():
            if unit.kind is units.Kind.TIMER and unit.next_elapse:
                return _relative(unit.next_elapse)
        return None

    # --------------------------------------------------------------- acoes

    def _on_scan(self, _):
        cmd = actions.scan_command(Path.home(), self.cfg.socket, self.cfg.quarantine)
        actions.run_in_terminal(cmd, self.cfg.terminal)

    def _on_quarantine(self, _):
        actions.open_path(self.cfg.quarantine)

    def _on_logs(self, _):
        actions.run_in_terminal(
            f"less {self.cfg.scan_log or self.cfg.log_file}", self.cfg.terminal
        )


def _relative(when: datetime) -> str:
    """'hoje 07:42' / 'amanhã 03:01' / '23/09 03:00'.

    Data absoluta so quando "hoje/ontem/amanha" nao resolve — quem olha a bandeja
    quer saber se ja rodou hoje, nao a data.
    """
    local = when.astimezone()
    today = datetime.now(timezone.utc).astimezone().date()
    delta = (local.date() - today).days
    prefixo = {0: "hoje", -1: "ontem", 1: "amanhã"}.get(delta)
    if prefixo:
        return f"{prefixo} {local:%H:%M}"
    return f"{local:%d/%m %H:%M}"
