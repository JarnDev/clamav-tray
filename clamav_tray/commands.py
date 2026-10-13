"""Iniciar e parar a varredura sob demanda — o mesmo codigo para o menu do tray,
para a linha de comando e, por ela, para a extensao do GNOME.

    clamav-tray --scan-home
    clamav-tray --scan-device <ponto-de-montagem | chave>
    clamav-tray --stop-scan

O QUE MUDOU E POR QUE. Ate a 0.4 o tray sabia que havia uma varredura sua (qual
alvo, se foi parada de proposito) porque FOI ELE que a iniciou: estava na memoria
do processo. Uma varredura lancada por outro processo — a extensao chamando a
linha de comando — ficaria orfa: sem notificacao no fim, e com "nao concluiu"
quando parada pelo painel. E o tray reiniciado no meio de uma varredura perdia o
fio dela pelo mesmo motivo.

Agora quem inicia grava scan.json no diretorio de execucao (alvo, midia, quando),
quem para marca `stopped`, e o tray ADOTA qualquer varredura em curso a partir
dele. O estado deixa de depender de quem clicou.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import actions, devices, progress
from . import config as config_mod
from .config import Config


@dataclass(frozen=True)
class ScanMeta:
    target: Path
    device_key: str | None = None
    """None = varredura da home. Senao, a chave da midia (Device.key)."""
    started_at: datetime | None = None
    stopped: bool = False
    """Parada de proposito: quem para nao precisa ser avisado de que "nao concluiu"."""


def meta_path() -> Path:
    return progress.runtime_dir() / "scan.json"


def write_atomic(path: Path, text: str) -> None:
    """Grava num temporario no MESMO diretorio e renomeia.

    rename e atomico no mesmo sistema de arquivos: quem le (o tray, a extensao)
    ve o arquivo antigo inteiro ou o novo inteiro, nunca a metade.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_meta() -> ScanMeta | None:
    try:
        d = json.loads(meta_path().read_text(encoding="utf-8"))
        started = d.get("started_at")
        return ScanMeta(
            target=Path(d["target"]),
            device_key=d.get("device_key"),
            started_at=datetime.fromisoformat(started) if started else None,
            stopped=bool(d.get("stopped")),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_meta(meta: ScanMeta) -> None:
    write_atomic(meta_path(), json.dumps({
        "target": str(meta.target),
        "device_key": meta.device_key,
        "started_at": meta.started_at.isoformat() if meta.started_at else None,
        "stopped": meta.stopped,
    }))


def _start(cfg: Config, target: Path, device_key: str | None, excludes) -> bool:
    # A sob demanda usa a quarentena do USUARIO: a do sistema e de root e ela roda
    # como voce. Sem destino gravavel o clamdscan aborta.
    dest = config_mod.ensure_user_quarantine(cfg.user_quarantine) if cfg.user_quarantine else None
    # Travas de varreduras interrompidas se acumulam; o clamdscan nao as remove.
    config_mod.clean_stale_locks(dest)
    # Meta ANTES de lancar: quando a unidade aparecer para o tray, o alvo ja esta la.
    _write_meta(ScanMeta(target, device_key, datetime.now(timezone.utc)))
    return actions.start_scan(target, cfg.socket, dest, excludes=excludes)


def scan_home(cfg: Config) -> bool:
    return _start(cfg, Path.home(), None, None)


def scan_device(cfg: Config, dev: devices.Device) -> bool:
    # excludes=[]: as regras da home (cache, node_modules) nao existem numa midia
    # removivel e so gastariam tempo do find.
    return _start(cfg, dev.mountpoint, dev.key, [])


def find_device(ident: str) -> devices.Device | None:
    """Pela chave (/dev/sdc1:/media/u/PEN) ou pelo ponto de montagem."""
    for dev in devices.list_removable():
        if ident in (dev.key, str(dev.mountpoint)):
            return dev
    return None


def stop_scan() -> bool:
    if (meta := read_meta()) is not None:
        _write_meta(ScanMeta(meta.target, meta.device_key, meta.started_at, stopped=True))
    return actions.stop_scan()


def main(argv: list[str], cfg: Config) -> int | None:
    """Despacha os comandos de varredura; None se nenhum estiver em argv."""
    if "--scan-home" in argv:
        ok = scan_home(cfg)
        print("varredura da home iniciada" if ok else "nao foi possivel iniciar a varredura")
        return 0 if ok else 1
    if "--scan-device" in argv:
        i = argv.index("--scan-device")
        if i + 1 >= len(argv):
            print("uso: clamav-tray --scan-device <ponto-de-montagem | chave>")
            return 2
        dev = find_device(argv[i + 1])
        if dev is None:
            print(f"midia removivel nao encontrada: {argv[i + 1]}")
            return 1
        ok = scan_device(cfg, dev)
        print(f"varredura de {dev.mountpoint} iniciada" if ok else "nao foi possivel iniciar")
        return 0 if ok else 1
    if "--stop-scan" in argv:
        return 0 if stop_scan() else 1
    return None
