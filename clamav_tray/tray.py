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

from . import actions, config as config_mod, history, scan, text, units, widgets  # noqa: E402
from .config import Config  # noqa: E402
from . import i18n  # noqa: E402
from .i18n import _  # noqa: E402
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
        if config_mod.changed_on_disk(self.cfg):
            self.cfg = config_mod.load()
            i18n.set_language(self.cfg.language)
            self.unit_ids = self.cfg.units or units.discover()
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
            return (_("Threat detected"), _("{n} file(s) quarantined", n=n))
        if running:
            return (_("Scanning"), "")
        if broken:
            nomes = ", ".join(self.cfg.label_for(u.id) for u in broken[:2])
            resto = " " + _("and {n} more", n=len(broken) - 2) if len(broken) > 2 else ""
            return (_("Attention"), _("{names} not healthy", names=f"{nomes}{resto}"))
        return (_("Protected"), _("all services running"))

    # ------------------------------------------------------------------ menu

    def _build_menu(self, state, running, broken, result, color) -> Gtk.Menu:
        menu = Gtk.Menu()
        menu.set_reserve_toggle_size(False)

        title, subtitle = self._headline(running, broken, result)
        menu.append(widgets.header(title, subtitle, color))
        menu.append(widgets.separator())

        # --- varredura ---------------------------------------------------
        menu.append(widgets.section(_("Scan")))

        if running:
            job = running[0]
            elapsed = job.elapsed_secs or 0
            total = self._last_duration or _FALLBACK_SCAN_SECS
            menu.append(
                widgets.progress_row(
                    _("In progress"),
                    min(elapsed / total, 0.99) if total else None,
                    _("for {duration}", duration=scan.human_duration(elapsed))
                    + (" · " + _("estimate {duration}", duration=scan.human_duration(total)) if self._last_duration else ""),
                )
            )
        else:
            menu.append(
                widgets.status_row(
                    _("Last"),
                    self._when_last(state),
                    widgets.RED if result.is_alarming else (
                        widgets.DIM if result.verdict is Verdict.UNKNOWN else widgets.GREEN
                    ),
                    text.describe(result),
                )
            )

        if nxt := self._next_scan(state):
            menu.append(widgets.status_row(_("Next"), nxt, widgets.DIM))

        # --- servicos ----------------------------------------------------
        menu.append(widgets.section(_("Services")))
        for unit in sorted(state.values(), key=lambda u: (u.kind.value, u.id)):
            # Timer aparece como "Proxima"; JOB aparece como "Ultima"/"Em andamento".
            # Socket e encanamento do daemon: mostra-lo duplicaria a mesma linha
            # ("ClamAV Daemon" e "Daemon" lado a lado, que foi o que saiu no teste).
            if unit.kind in (units.Kind.TIMER, units.Kind.JOB):
                continue
            if unit.id.endswith(".socket"):
                continue
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
                    _("History"), _("unavailable"), widgets.DIM,
                    _("no journal access (group adm or systemd-journal)"),
                )
            )

        # --- acoes -------------------------------------------------------
        menu.append(widgets.separator())
        menu.append(
            widgets.action(_("Scan my home now"), "media-playback-start-symbolic", self._on_scan)
        )
        if self.cfg.quarantine:
            menu.append(widgets.action(_("Open quarantine"), "folder-symbolic", self._on_quarantine))
        if self.cfg.scan_log or self.cfg.log_file:
            menu.append(widgets.action(_("View logs"), "text-x-generic-symbolic", self._on_logs))
        menu.append(widgets.action(_("Settings"), "preferences-system-symbolic", self._on_settings))
        menu.append(widgets.separator())
        menu.append(widgets.action(_("Quit"), "application-exit-symbolic", lambda *_a: Gtk.main_quit()))

        menu.show_all()
        return menu

    # ------------------------------------------------------------- formatos

    def _when_last(self, state) -> str:
        for unit in state.values():
            if unit.kind is units.Kind.JOB and unit.finished_at:
                return text.relative_time(unit.finished_at)
        return ""

    def _next_scan(self, state) -> str | None:
        for unit in state.values():
            if unit.kind is units.Kind.TIMER and unit.next_elapse:
                return text.relative_time(unit.next_elapse)
        return None

    # --------------------------------------------------------------- acoes

    def _on_scan(self, *_a):
        cmd = actions.scan_command(Path.home(), self.cfg.socket, self.cfg.quarantine)
        actions.run_in_terminal(cmd, self.cfg.terminal)

    def _on_quarantine(self, *_a):
        actions.open_path(self.cfg.quarantine)

    def _on_settings(self, *_a):
        """Abre o arquivo de config, criando um modelo comentado se nao existir.

        Nao ha dialogo de preferencias em GTK aqui de proposito: seria mais codigo
        que o resto do programa junto, e a edicao e rara. O arquivo e recarregado
        sozinho ao salvar, entao o efeito e o mesmo sem a superficie.
        """
        actions.open_path(config_mod.ensure_file())

    def _on_logs(self, *_a):
        actions.run_in_terminal(
            f"less {self.cfg.scan_log or self.cfg.log_file}", self.cfg.terminal
        )
