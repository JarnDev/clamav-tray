"""scan.json: o estado da varredura sob demanda deixou de morar na memoria de quem
a iniciou. Quem inicia grava, quem para marca, e o tray adota."""

import os
import tempfile
from pathlib import Path

from clamav_tray import commands


def _em_runtime_temporario(fn):
    antes = os.environ.get("XDG_RUNTIME_DIR")
    with tempfile.TemporaryDirectory() as d:
        os.environ["XDG_RUNTIME_DIR"] = d
        try:
            return fn(Path(d))
        finally:
            if antes is None:
                os.environ.pop("XDG_RUNTIME_DIR", None)
            else:
                os.environ["XDG_RUNTIME_DIR"] = antes


def test_sem_meta_e_none():
    _em_runtime_temporario(lambda d: commands.read_meta() is None or (_ for _ in ()).throw(AssertionError))


def test_meta_ida_e_volta_e_parada():
    def caso(d):
        from datetime import datetime, timezone
        quando = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)
        commands._write_meta(commands.ScanMeta(Path("/media/u/PEN"), "/dev/sdc1:/media/u/PEN", quando))
        m = commands.read_meta()
        assert m.target == Path("/media/u/PEN") and m.device_key == "/dev/sdc1:/media/u/PEN"
        assert m.started_at == quando and m.stopped is False
        assert commands.meta_path() == d / "clamav-tray" / "scan.json"
        # parar marca stopped sem perder o resto (actions.stop_scan e substituido:
        # aqui nao ha systemd de verdade para parar).
        orig = commands.actions.stop_scan
        commands.actions.stop_scan = lambda: True
        try:
            assert commands.stop_scan() is True
        finally:
            commands.actions.stop_scan = orig
        m = commands.read_meta()
        assert m.stopped is True and m.device_key == "/dev/sdc1:/media/u/PEN"
    _em_runtime_temporario(caso)


def test_meta_corrompida_e_none():
    def caso(d):
        commands.meta_path().parent.mkdir(parents=True)
        commands.meta_path().write_text("{meio arquivo")
        assert commands.read_meta() is None
    _em_runtime_temporario(caso)


def test_escrita_atomica_nao_deixa_temporario():
    def caso(d):
        alvo = d / "x" / "state.json"
        commands.write_atomic(alvo, '{"a": 1}')
        commands.write_atomic(alvo, '{"a": 2}')
        assert alvo.read_text() == '{"a": 2}'
        assert [p.name for p in alvo.parent.iterdir()] == ["state.json"]
    _em_runtime_temporario(caso)
