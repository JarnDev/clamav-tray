"""Camada grafica: bandeja, menu, icone.

Modulo 5 e ULTIMO da migracao para Rust, de proposito. E onde mora o estado
compartilhado entre callbacks, e onde depurar e pior: quando a bandeja nao aparece,
nao ha mensagem de erro, so ausencia.

Duas bibliotecas de AppIndicator convivem no mundo e nenhuma esta em todo lugar:
o Ubuntu costuma trazer a antiga (AppIndicator3), Fedora e Arch tendem a Ayatana.
Tentamos as duas. Assumir uma quebra metade das distros.
"""

from __future__ import annotations

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

from . import actions, history, scan, units  # noqa: E402
from .config import Config  # noqa: E402

ICONS = {
    "ok": "security-high-symbolic",
    "busy": "security-medium-symbolic",
    "warn": "security-low-symbolic",
}


class Tray:
    def __init__(self, cfg: Config):
        if _INDICATOR is None:
            raise RuntimeError(
                "nenhum AppIndicator encontrado — instale gir1.2-appindicator3-0.1 "
                "ou gir1.2-ayatanaappindicator3-0.1"
            )
        self.cfg = cfg
        self.unit_ids = cfg.units or units.discover()
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

        # Precedencia: ameaca > varrendo > servico caido > ok. Uma infeccao nunca
        # pode ser escondida por uma varredura em andamento.
        if result.is_alarming:
            icon = ICONS["warn"]
        elif running:
            icon = ICONS["busy"]
        elif any(not u.is_healthy for u in state.values()):
            icon = ICONS["warn"]
        else:
            icon = ICONS["ok"]
        self.indicator.set_icon_full(icon, "ClamAV")

        self.indicator.set_menu(self._build_menu(state, running, result))
        return True  # mantem o timer vivo

    def _scan_unit(self, state: dict[str, units.Unit]) -> str | None:
        for unit_id, unit in state.items():
            if unit.kind is units.Kind.JOB:
                return unit_id
        return None

    # ------------------------------------------------------------------ menu

    def _build_menu(self, state, running, result) -> Gtk.Menu:
        menu = Gtk.Menu()

        for unit in sorted(state.values(), key=lambda u: u.id):
            if unit.kind is units.Kind.TIMER:
                continue
            dot = "🔍" if unit.is_running_job else ("🟢" if unit.is_healthy else "🔴")
            label = self.cfg.label_for(unit.id)
            if unit.is_running_job and (secs := unit.elapsed_secs) is not None:
                label += f" — há {scan.human_duration(secs)}"
            self._info(menu, f"{dot} {label}")

        self._sep(menu)

        if running:
            self._info(menu, "🔍 Varredura em andamento")
        else:
            verdict = scan.describe(result)
            mark = "⚠️" if result.is_alarming else "✅"
            self._info(menu, f"{mark} Última: {verdict}")

        for unit in state.values():
            if unit.kind is units.Kind.TIMER and unit.next_elapse:
                when = unit.next_elapse.astimezone().strftime("%d/%m %H:%M")
                self._info(menu, f"⏱ Próxima: {when}")
                break

        if not history.journal_readable() and self.cfg.scan_log is None:
            self._info(menu, "ℹ️ histórico indisponível (sem acesso ao journal)")

        self._sep(menu)
        self._action(menu, "▶ Varrer minha home agora", self._on_scan)
        if self.cfg.quarantine:
            self._action(menu, "📂 Abrir quarentena", self._on_quarantine)
        if self.cfg.scan_log or self.cfg.log_file:
            self._action(menu, "📄 Ver logs", self._on_logs)
        self._sep(menu)
        self._action(menu, "Sair", lambda _: Gtk.main_quit())

        menu.show_all()
        return menu

    def _info(self, menu, text):
        item = Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        menu.append(item)

    def _action(self, menu, text, handler):
        item = Gtk.MenuItem(label=text)
        item.connect("activate", handler)
        menu.append(item)

    def _sep(self, menu):
        menu.append(Gtk.SeparatorMenuItem())

    # --------------------------------------------------------------- acoes

    def _on_scan(self, _):
        from pathlib import Path

        cmd = actions.scan_command(Path.home(), self.cfg.socket, self.cfg.quarantine)
        actions.run_in_terminal(cmd, self.cfg.terminal)

    def _on_quarantine(self, _):
        actions.open_path(self.cfg.quarantine)

    def _on_logs(self, _):
        actions.run_in_terminal(f"less {self.cfg.scan_log or self.cfg.log_file}", self.cfg.terminal)
