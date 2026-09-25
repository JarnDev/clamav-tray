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

# Um escudo parado nao diz o que esta acontecendo. Durante a varredura o icone
# vira LUPA e o indicador ganha um rotulo com o tempo decorrido — texto ao lado do
# icone comunica "trabalhando" melhor que qualquer desenho, e ainda informa quanto.
ICONS = {
    "ok": "security-high-symbolic",       # escudo: protegido
    "busy": "system-search-symbolic",     # lupa: procurando
    "warn": "security-medium-symbolic",   # escudo parcial: servico caido
    "threat": "security-low-symbolic",    # escudo rompido: ameaca
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
        state = units.query_all(self.unit_ids)
        job = units.pick_scan_unit(state)
        running = [u for u in state.values() if u.is_running_job]
        # Rede de seguranca: varredura lancada fora do tray (terminal, cron) nao e
        # unidade nenhuma, mas o disco esta trabalhando do mesmo jeito.
        loose_scan = not running and units.scan_process_running()
        result = scan.parse_summary(
            history.last_summary(
                self.cfg.scan_log,
                job.id if job else None,
                user=bool(job and job.user_scope),
            ) or ""
        )
        if result.duration_secs:
            self._last_duration = result.duration_secs

        # Precedencia: ameaca > varrendo > servico caido > ok. Uma infeccao nunca
        # pode ser escondida por uma varredura em andamento.
        broken = [u for u in state.values() if not u.is_healthy]
        if result.is_alarming:
            key, mark = "threat", widgets.BAD
        elif running or loose_scan:
            key, mark = "busy", widgets.BUSY
        elif broken:
            key, mark = "warn", widgets.WARN
        else:
            key, mark = "ok", widgets.OK

        self.indicator.set_icon_full(ICONS[key], "ClamAV")
        self.indicator.set_label(self._indicator_label(running, loose_scan, result), "")
        self.indicator.set_menu(
            self._build_menu(state, running, broken, result, mark, loose_scan)
        )
        return True  # mantem o timer vivo

    def _indicator_label(self, running, loose_scan, result) -> str:
        """Texto ao lado do icone na barra. Vazio em repouso — indicador que fala o
        tempo todo vira ruido; o que fala so quando ha o que dizer, e lido."""
        if result.is_alarming:
            return f"⚠ {result.infected}"
        if running and (secs := running[0].elapsed_secs):
            return scan.human_duration(secs)
        if running or loose_scan:
            return "…"
        return ""

    def _headline(self, running, broken, result, loose=False) -> tuple[str, str]:
        if result.is_alarming:
            n = result.infected
            return (_("Threat detected"), _("{n} file(s) quarantined", n=n))
        if running or loose:
            return (_("Scanning"), "")
        if broken:
            nomes = ", ".join(self.cfg.label_for(u.id) for u in broken[:2])
            resto = " " + _("and {n} more", n=len(broken) - 2) if len(broken) > 2 else ""
            return (_("Attention"), _("{names} not healthy", names=f"{nomes}{resto}"))
        return (_("Protected"), _("all services running"))

    # ------------------------------------------------------------------ menu

    def _build_menu(self, state, running, broken, result, mark, loose_scan=False) -> Gtk.Menu:
        menu = Gtk.Menu()
        menu.set_reserve_toggle_size(False)

        title, subtitle = self._headline(running, broken, result, loose_scan)
        menu.append(widgets.header(title, subtitle, mark))
        menu.append(widgets.separator())

        # --- varredura ---------------------------------------------------
        menu.append(widgets.section(_("Scan")))

        if running or loose_scan:
            job = running[0] if running else None
            elapsed = (job.elapsed_secs if job else None) or 0
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
                    widgets.BAD if result.is_alarming else (
                        widgets.IDLE if result.verdict is Verdict.UNKNOWN else widgets.OK
                    ),
                    text.describe(result),
                )
            )

        if nxt := self._next_scan(state):
            menu.append(widgets.status_row(_("Next"), nxt, widgets.IDLE))

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
                    widgets.OK if unit.is_healthy else widgets.WARN,
                )
            )

        if self.cfg.quarantine:
            n = config_mod.quarantine_count(self.cfg.quarantine)
            if n is None:
                value, mark = _("needs root to list"), widgets.IDLE
            elif n == 0:
                value, mark = _("empty"), widgets.OK
            else:
                value = _("{n} file" if n == 1 else "{n} files", n=n)
                mark = widgets.WARN
            menu.append(widgets.status_row(_("Quarantine"), value, mark,
                                           str(self.cfg.quarantine)))

        if self.cfg.user_quarantine:
            n = config_mod.quarantine_count(self.cfg.user_quarantine)
            # So aparece quando tem algo dentro: diretorio vazio nao merece linha.
            if n:
                menu.append(widgets.status_row(
                    _("Quarantine (mine)"),
                    _("{n} file" if n == 1 else "{n} files", n=n),
                    widgets.WARN, str(self.cfg.user_quarantine)))

        if not history.journal_readable() and self.cfg.scan_log is None:
            menu.append(
                widgets.status_row(
                    _("History"), _("unavailable"), widgets.IDLE,
                    _("no journal access (group adm or systemd-journal)"),
                )
            )

        # --- acoes -------------------------------------------------------
        menu.append(widgets.separator())
        if running:
            # Varredura lancada por nos: da para parar, entao o botao VIRA parar.
            menu.append(widgets.action(
                _("Stop scan"), "media-playback-stop-symbolic", self._on_stop))
        elif loose_scan:
            # Varredura de fora: sabemos que existe, mas nao e nossa para interromper.
            item = widgets.action(
                _("Scan my home now"), "media-playback-start-symbolic", lambda *_a: None)
            item.set_sensitive(False)
            menu.append(item)
        else:
            menu.append(widgets.action(
                _("Scan my home now"), "media-playback-start-symbolic", self._on_scan))
        if self.cfg.quarantine:
            menu.append(widgets.action(_("List quarantine"), "folder-symbolic", self._on_quarantine))
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
        # A varredura sob demanda usa a quarentena do USUARIO: a do sistema e de
        # root e ela roda como voce. Sem destino gravavel o clamdscan aborta.
        dest = config_mod.ensure_user_quarantine(self.cfg.user_quarantine) \
            if self.cfg.user_quarantine else None
        actions.start_scan(Path.home(), self.cfg.socket, dest)

    def _on_stop(self, *_a):
        actions.stop_scan()

    def _on_quarantine(self, *_a):
        actions.list_quarantine(self.cfg.quarantine, self.cfg.terminal)

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
