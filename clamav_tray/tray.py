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
import os
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

from . import (actions, config as config_mod, history, progress,  # noqa: E402
               quarantine, scan, text, units, widgets)
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
        # Conta so os bytes novos da saida a cada atualizacao; reler um milhao de
        # linhas de 10 em 10 segundos custaria mais que a propria varredura.
        self._counter = progress.LineCounter(progress.output_path())
        self._list_total: int | None = None
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

    def _scan_card(self, elapsed: int, ours: bool) -> list:
        """Bloco de informacoes da varredura em curso.

        Uma linha por item, cada uma um Gtk.MenuItem proprio — e o unico arranjo
        que renderiza de forma confiavel dentro de um menu do GTK 3.
        """
        rows = [widgets.status_row(_("In progress"), "", widgets.BUSY)]
        pr = self._progress_data()
        rows.append(widgets.progress_bar(pr.fraction if pr else None))

        if pr:
            rows.append(widgets.card_line(
                _("Files"), f"{_thousands(pr.done)} / {_thousands(pr.total)}"))
            remaining = max(pr.total - pr.done, 0)
            rows.append(widgets.card_line(_("Remaining"), _thousands(remaining)))
            if elapsed > 0 and pr.done > 0:
                rows.append(widgets.card_line(
                    _("Rate"), _("{n}/s", n=max(pr.done // elapsed, 1))))

        rows.append(widgets.card_line(
            _("Elapsed"), scan.human_duration(elapsed) if elapsed else "—"))

        found = self._counter.found if ours else 0
        rows.append(widgets.card_line(
            _("Infected"),
            _thousands(found) if found else _("none so far"),
            widgets.BAD if found else "",
        ))

        if ours:
            rows.append(widgets.card_line(_("Target"), str(Path.home())))
            if self.cfg.user_quarantine:
                rows.append(widgets.card_line(
                    _("Moves to"), str(self.cfg.user_quarantine)))
        else:
            # Varredura de fora: sabemos que existe pelo processo, e so.
            rows.append(widgets.card_line(_("Source"), _("started outside the tray")))
        return rows

    def _progress_data(self):
        """Fracao/contagem da varredura, da fonte que responder."""
        pr = progress.from_counter_file(
            self.cfg.scan_log.parent if self.cfg.scan_log else None
        )
        if pr is not None:
            return pr
        if self._list_total is None:
            # O tray pode ter reiniciado no meio de uma varredura; o total esta no
            # proprio arquivo de lista.
            self._list_total = progress.count_lines(progress.list_path()) or None
        if self._list_total:
            done = self._counter.count()
            if done:
                return progress.Progress(done=done, total=self._list_total)
        return None

    def _progress(self, elapsed: int) -> tuple[float | None, str]:
        """Fracao e legenda da barra.

        Ordem das fontes: contador publicado por quem varre (convencao), depois a
        nossa propria contagem de linhas, depois nada. "Nada" vira barra pulsante e
        so o tempo decorrido — honesto, em vez de uma porcentagem inventada.
        """
        base = _("for {duration}", duration=scan.human_duration(elapsed))

        pr = progress.from_counter_file(
            self.cfg.scan_log.parent if self.cfg.scan_log else None
        )
        if self._list_total is None:
            # O tray pode ter reiniciado no meio de uma varredura. O total esta no
            # proprio arquivo de lista, entao nao ha por que perde-lo.
            self._list_total = progress.count_lines(progress.list_path()) or None

        if pr is None and (total := self._list_total):
            done = self._counter.count()
            if done:
                pr = progress.Progress(done=done, total=total)

        if pr and pr.fraction is not None:
            return pr.fraction, f"{base} · {pr.done:,}/{pr.total:,}".replace(",", ".")
        return None, base

    def _indicator_label(self, running, loose_scan, result) -> str:
        """Texto ao lado do icone na barra. Vazio em repouso — indicador que fala o
        tempo todo vira ruido; o que fala so quando ha o que dizer, e lido."""
        if result.is_alarming:
            return f"⚠ {result.infected}"
        if running and (secs := running[0].elapsed_secs):
            pr = self._progress_data()
            if pr and pr.fraction is not None:
                return f"{pr.percent}%"
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
        """Quatro blocos separados por linha, sem rotulo de secao.

        Rotulo de secao custa uma linha para dizer o que o agrupamento ja diz. Num
        menu de bandeja, onde nao ha negrito nem cor — o dbusmenu descarta markup —,
        a hierarquia sai de recuo, simbolo e separador. So isso.
        """
        menu = Gtk.Menu()
        menu.set_reserve_toggle_size(False)

        # --- 1. o que esta acontecendo -----------------------------------
        if running or loose_scan:
            job = running[0] if running else None
            for row in self._scan_card((job.elapsed_secs if job else None) or 0, bool(job)):
                menu.append(row)
        else:
            for row in self._idle_card(state, broken, result, mark):
                menu.append(row)

        # --- 2. servicos, separados por barramento -----------------------
        # Sistema e usuario sao contextos diferentes de privilegio, nao detalhe de
        # implementacao: o que roda como root e o que roda como voce respondem a
        # perguntas diferentes quando algo da errado.
        sistema = [u for u in state.values()
                   if not u.user_scope and u.kind is units.Kind.DAEMON
                   and not u.id.endswith(".socket")]
        usuario = [u for u in state.values() if u.user_scope]

        if sistema:
            menu.append(widgets.separator())
            menu.append(widgets.section(_("System")))
            for unit in sorted(sistema, key=lambda u: u.id):
                menu.append(self._service_row(unit))

        if usuario:
            menu.append(widgets.separator())
            menu.append(widgets.section(_("User")))
            for unit in sorted(usuario, key=lambda u: u.id):
                if unit.kind is units.Kind.JOB:
                    # Tarefa encerrada nao e servico: ponto verde ali diria "no ar"
                    # sobre algo que ja terminou. Mostra o desfecho, nao a saude.
                    ok = unit.result in ("success", "unknown")
                    when = (text.relative_time(unit.finished_at)
                            if unit.finished_at else "")
                    menu.append(widgets.status_row(
                        _("On-demand scan"),
                        (_("finished {when}", when=when) if ok and when
                         else _("finished") if ok else _("failed")),
                        widgets.IDLE if ok else widgets.WARN,
                    ))
                else:
                    menu.append(self._service_row(unit))

        # --- 3. quarentena, uma subsecao por dono -------------------------
        for row in self._quarantine_rows():
            menu.append(row)

        # --- 4. acoes -----------------------------------------------------
        menu.append(widgets.separator())
        if running:
            menu.append(widgets.action(_("Stop scan"), "media-playback-stop-symbolic", self._on_stop))
        elif loose_scan:
            item = widgets.action(_("Scan my home now"), "media-playback-start-symbolic", lambda *_a: None)
            item.set_sensitive(False)
            menu.append(item)
        else:
            menu.append(widgets.action(_("Scan my home now"), "media-playback-start-symbolic", self._on_scan))

        if self.cfg.scan_log or self.cfg.log_file:
            menu.append(widgets.action(_("View logs"), "text-x-generic-symbolic", self._on_logs))
        menu.append(widgets.action(_("Settings"), "preferences-system-symbolic", self._on_settings))
        menu.append(widgets.separator())
        menu.append(widgets.action(_("Quit"), "application-exit-symbolic", lambda *_a: Gtk.main_quit()))

        menu.show_all()
        return menu

    def _service_row(self, unit) -> object:
        label = self.cfg.label_for(unit.id)
        # Estado so aparece quando e ANORMAL: "running" repetido em toda linha e
        # ruido, e o ponto verde ja diz.
        if not unit.is_healthy:
            label += f" · {unit.sub_state}"
        return widgets.status_row(
            label, "", widgets.OK if unit.is_healthy else widgets.WARN)

    def _idle_card(self, state, broken, result, mark) -> list:
        """Bloco de topo quando nao ha varredura em curso."""
        title, subtitle = self._headline([], broken, result)
        rows = [widgets.status_row(title, "", mark)]
        # "todos os servicos no ar" e redundante: a lista de servicos vem logo
        # abaixo, com um ponto verde cada. Subtitulo so quando ha algo a explicar.
        if subtitle and (broken or result.is_alarming):
            rows.append(widgets.line(subtitle))

        when = self._when_last(state)
        if when:
            rows.append(widgets.line(_("Last scan {when}", when=when)))
        rows.append(widgets.line(text.describe(result).capitalize()))
        if nxt := self._next_scan(state):
            rows.append(widgets.line(_("Next {when}", when=nxt)))
        return rows

    def _quarantine_rows(self) -> list:
        """Uma subsecao por dono.

        Sao duas quarentenas com donos e regras diferentes, e tratar as duas como
        uma so era o que produzia a linha enganosa "precisa de root para listar"
        mesmo quando a do usuario estava perfeitamente legivel. Root precisa de
        root; a sua, nao.
        """
        rows = []

        stats = quarantine.read_stats()
        if stats or self.cfg.quarantine:
            path = (stats.source if stats and stats.source else self.cfg.quarantine)
            if stats:
                desc = _("{n} file" if stats.count == 1 else "{n} files", n=stats.count)
                if stats.bytes:
                    desc += f" · {quarantine.human_bytes(stats.bytes)}"
                mark = widgets.WARN if stats.count else widgets.OK
            else:
                desc, mark = _("needs root to list"), widgets.IDLE
            rows.append(widgets.status_action(
                "root", desc, mark, self._on_quarantine_system))
            if stats and stats.checked_at:
                rows.append(widgets.line(
                    _("checked {when}", when=text.relative_time(stats.checked_at))))
            if path:
                rows.append(widgets.line(_shorten(path)))

        if self.cfg.user_quarantine:
            n = config_mod.quarantine_count(self.cfg.user_quarantine)
            if n is None:
                desc, mark = _("unreadable"), widgets.IDLE
            elif n == 0:
                desc, mark = _("empty"), widgets.OK
            else:
                desc = _("{n} file" if n == 1 else "{n} files", n=n)
                mark = widgets.WARN
            rows.append(widgets.status_action(
                _current_user(), desc, mark, self._on_quarantine_user))
            rows.append(widgets.line(_shorten(self.cfg.user_quarantine)))

        if rows:
            rows.insert(0, widgets.section(_("Quarantine")))
            rows.insert(0, widgets.separator())
        return rows

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
        # Limpa travas de varreduras interrompidas antes de comecar: elas se
        # acumulam e o clamdscan nao as remove sozinho.
        config_mod.clean_stale_locks(dest)
        actions.start_scan(Path.home(), self.cfg.socket, dest)
        # A lista acabou de ser escrita; guardar o total e o que da escala a barra.
        self._list_total = progress.count_lines(progress.list_path()) or None

    def _on_stop(self, *_a):
        actions.stop_scan()

    def _on_quarantine_system(self, *_a):
        actions.list_quarantine(self.cfg.quarantine, self.cfg.terminal)

    def _on_quarantine_user(self, *_a):
        # A do usuario nao precisa de sudo: e nossa.
        actions.list_quarantine(
            self.cfg.user_quarantine, self.cfg.terminal, privileged=False)

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


def _thousands(n: int) -> str:
    """1131791 -> 1.131.791. Numero grande sem separador vira borrao."""
    return f"{n:,}".replace(",", ".")


def _current_user() -> str:
    """Nome do usuario, para a quarentena dele nao se chamar "minha" — num menu
    que fala de root ao lado, o nome real e o que deixa o par legivel."""
    import getpass
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER", "user")


def _shorten(path) -> str:
    """/home/oranos/.local/... -> ~/.local/... — caminho inteiro domina a linha."""
    text_ = str(path)
    home = str(Path.home())
    return "~" + text_[len(home):] if text_.startswith(home) else text_
