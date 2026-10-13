"""Testes do `--dump --json` — o contrato de docs/json.md.

Quem le esta saida (script, Glance, o `clamav-status` em Rust) depende dos NOMES
e dos TIPOS. Estes testes falham se um campo sumir ou mudar de tipo, que e
exatamente a mudanca que exige subir `schema`.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clamav_tray.config import Config
from clamav_tray.report import SCHEMA, build, status
from clamav_tray.scan import parse_summary
from clamav_tray.units import Kind, Unit

TZ = timezone(timedelta(hours=-3))

DAEMON = Unit(id="clamav-daemon.service", kind=Kind.DAEMON, active_state="active",
              sub_state="running", result="success",
              started_at=datetime(2026, 10, 9, 17, 48, 11, tzinfo=TZ))
DAEMON_CAIDO = Unit(id="clamav-daemon.service", kind=Kind.DAEMON, active_state="failed",
                    sub_state="failed", result="exit-code")
TIMER = Unit(id="clamav-scan.timer", kind=Kind.TIMER, active_state="active",
             sub_state="waiting", result="success",
             next_elapse=datetime(2026, 10, 14, 3, 2, 45, tzinfo=TZ))
AGENDADA = Unit(id="clamav-scan.service", kind=Kind.JOB, active_state="inactive",
                sub_state="dead", result="success", exit_status=0,
                finished_at=datetime(2026, 10, 13, 7, 54, 11, tzinfo=TZ))
RODANDO = Unit(id="clamav-scan.service", kind=Kind.JOB, active_state="active",
               sub_state="running", result="success")

LIMPA = parse_summary("""\
----------- SCAN SUMMARY -----------
Infected files: 0
Total errors: 6
Time: 16317.863 sec (271 m 57 s)
""")
INFECTADA = parse_summary("""\
----------- SCAN SUMMARY -----------
Scanned files: 12
Infected files: 1
Total errors: 0
""")

CFG = Config(socket=Path("/var/run/clamav/clamd.ctl"), scan_log=Path("/var/log/clamav/scan.log"))


def _estado(*units):
    return {u.id: u for u in units}


def test_formato_e_tipos():
    d = build(CFG, _estado(DAEMON, TIMER, AGENDADA), AGENDADA, LIMPA, version="0.3.0")
    assert d["schema"] == SCHEMA == 1
    assert d["version"] == "0.3.0"
    # Campos novos nao sobem o schema, mas entram aqui de proposito: cada um e uma
    # promessa a quem le. (0.5: producer, generated_at, media, quarantine, progress.)
    assert set(d) == {"schema", "version", "producer", "generated_at", "status", "units",
                      "scan", "media", "quarantine", "paths"}
    unidade = d["units"][0]
    assert set(unidade) == {"id", "label", "kind", "user_scope", "active_state", "sub_state",
                            "result", "healthy", "running", "exit_status", "started_at",
                            "finished_at", "next_run"}
    assert set(d["scan"]) == {"unit", "running", "outside_systemd", "verdict", "infected",
                              "unreadable", "scanned", "duration_secs", "finished_at",
                              "progress"}
    assert set(d["paths"]) == {"socket", "scan_log", "daemon_log", "quarantine", "user_quarantine"}
    # Tem de sobreviver a json.dumps sem default=: nada de datetime ou Path cru.
    json.dumps(d)


def test_unidades_ordenadas_e_horario_com_fuso():
    d = build(CFG, _estado(TIMER, DAEMON, AGENDADA), AGENDADA, LIMPA)
    assert [u["id"] for u in d["units"]] == sorted(u["id"] for u in d["units"])
    timer = next(u for u in d["units"] if u["kind"] == "timer")
    assert timer["next_run"] == "2026-10-14T03:02:45-03:00"


def test_ausencia_e_null_nao_omissao():
    d = build(Config(), _estado(DAEMON), None, parse_summary(""))
    assert d["scan"]["unit"] is None
    assert d["scan"]["verdict"] == "unknown"
    assert d["scan"]["scanned"] is None
    assert d["paths"]["socket"] is None
    assert d["units"][0]["finished_at"] is None


def test_resultado_da_varredura():
    d = build(CFG, _estado(AGENDADA), AGENDADA, LIMPA)
    assert d["scan"] == {
        "unit": "clamav-scan.service", "running": False, "outside_systemd": False,
        "verdict": "clean", "infected": 0, "unreadable": 6, "scanned": None,
        "duration_secs": 16317, "finished_at": "2026-10-13T07:54:11-03:00",
        "progress": None,
    }


def test_status_segue_a_precedencia_do_icone():
    # Ameaca vence varredura em andamento: uma infeccao nunca fica escondida.
    assert status(_estado(RODANDO), INFECTADA) == "threat"
    assert status(_estado(RODANDO, DAEMON), LIMPA) == "busy"
    assert status(_estado(DAEMON_CAIDO), LIMPA) == "warn"
    assert status(_estado(DAEMON, TIMER, AGENDADA), LIMPA) == "ok"
    # Nenhuma unidade (Fedora recem-instalado: nada vem habilitado) nao e "ok".
    assert status({}, parse_summary("")) == "warn"
    # Varredura lancada fora do systemd tambem e trabalho em andamento.
    assert status(_estado(DAEMON), LIMPA, loose_scan=True) == "busy"


def test_varredura_fora_do_systemd():
    d = build(CFG, _estado(DAEMON), None, LIMPA, loose_scan=True)
    assert d["scan"]["running"] is True
    assert d["scan"]["outside_systemd"] is True


def test_produtor_e_horario_de_geracao():
    agora = datetime(2026, 10, 13, 18, 0, 0, tzinfo=TZ)
    d = build(CFG, _estado(DAEMON), None, LIMPA, producer="tray", now=agora)
    assert d["producer"] == "tray"
    assert d["generated_at"] == "2026-10-13T18:00:00-03:00"
    assert build(CFG, _estado(DAEMON), None, LIMPA)["producer"] == "dump"


def test_progresso_da_varredura_em_curso():
    from clamav_tray.progress import Progress
    d = build(CFG, _estado(RODANDO), RODANDO, parse_summary(""),
              progress=Progress(done=57000, total=100000))
    assert d["scan"]["progress"] == {"done": 57000, "total": 100000}
    assert d["scan"]["running"] is True


def test_midia_varrida_e_nao_varrida():
    from clamav_tray.devices import Device
    pen = Device(source="/dev/sdc1", mountpoint=Path("/media/u/PEN"), label="PEN",
                 size_bytes=16 * 1024 ** 3)
    cd = Device(source="/dev/sr0", mountpoint=Path("/media/u/CD"), label="CD")
    quando = datetime(2026, 10, 13, 17, 0, tzinfo=TZ)
    d = build(CFG, _estado(DAEMON), None, LIMPA, media=[pen, cd],
              media_scanned={cd.key: (quando, 1, 1)})
    assert d["media"][0] == {"key": "/dev/sdc1:/media/u/PEN", "label": "PEN",
                             "mountpoint": "/media/u/PEN", "size_bytes": 16 * 1024 ** 3,
                             "scanned": None}
    # CD somente leitura: encontrou 1 e nao isolou 1.
    assert d["media"][1]["scanned"] == {"at": "2026-10-13T17:00:00-03:00",
                                        "infected": 1, "not_contained": 1}


def test_quarentena_desconhecida_e_null():
    d = build(CFG, _estado(DAEMON), None, LIMPA,
              quarantine={"system": None, "user": {"count": 2}})
    assert d["quarantine"] == {"system": None, "user": {"count": 2}}
    # Sem informar, o campo existe e e null — ausencia nao e omissao.
    assert build(CFG, _estado(DAEMON), None, LIMPA)["quarantine"] is None
    json.dumps(d)
