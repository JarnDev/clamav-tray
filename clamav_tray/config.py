"""Descoberta de caminhos e configuracao opcional.

Modulo 3 da migracao.

A premissa: configuracao deve ser OPCIONAL. O programa pergunta ao sistema em vez
de exigir que o usuario declare. Duas fontes de descoberta:

- `clamconf`, que vem do proprio ClamAV e nao do empacotador. E por isso que
  `LocalSocket` sai certo tanto no Debian (/var/run/clamav/clamd.ctl) quanto no
  Fedora (/run/clamd.scan/clamd.sock) sem nenhuma tabela por distro aqui dentro.
- o glob de unidades em units.discover().

O arquivo TOML existe para sobrescrever e para rotular, nunca como pre-requisito.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
) / "clamav-tray" / "config.toml"

# Rotulos legiveis para as unidades mais comuns. Puramente cosmetico: unidade
# desconhecida aparece com o proprio nome, que e melhor que nao aparecer.
KNOWN_LABELS = {
    "clamav-daemon.service": "ClamAV Daemon",
    "clamd@scan.service": "ClamAV Daemon",
    "clamav-freshclam.service": "Freshclam (updates)",
    "clamav-clamonacc.service": "On-Access Scan",
}


@dataclass
class Config:
    socket: Path | None = None
    log_file: Path | None = None
    """Log do DAEMON (clamd), vindo do clamconf. NAO contem SCAN SUMMARY."""
    scan_log: Path | None = None
    """Log da VARREDURA. Outra coisa: e onde o SCAN SUMMARY aparece."""
    database_dir: Path | None = None
    quarantine: Path | None = None
    units: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    refresh_secs: int = 10
    terminal: str | None = None

    def label_for(self, unit_id: str) -> str:
        if unit_id in self.labels:
            return self.labels[unit_id]
        if unit_id in KNOWN_LABELS:
            return KNOWN_LABELS[unit_id]
        # clamav-scan-downloads.service -> "Scan Downloads"
        stem = unit_id.rsplit(".", 1)[0]
        stem = re.sub(r"^clamav?-", "", stem).replace("-", " ").replace("_", " ")
        return stem.title() or unit_id


def clamconf_paths() -> dict[str, str]:
    """Configuracao efetiva do ClamAV, perguntada a ele mesmo.

    Ausencia do clamconf nao e erro: o programa segue com o que o TOML disser, ou
    sem caminho nenhum (o menu apenas esconde as acoes que dependeriam dele).
    """
    if not shutil.which("clamconf"):
        return {}
    try:
        out = subprocess.run(
            ["clamconf", "-n"], capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}

    found = {}
    for line in out.splitlines():
        # clamconf imprime:  LocalSocket = "/var/run/clamav/clamd.ctl"
        if m := re.match(r'^\s*(\w+)\s*=\s*"(.*)"\s*$', line):
            found.setdefault(m.group(1), m.group(2))
    return found


def load() -> Config:
    cfg = Config()

    paths = clamconf_paths()
    if v := paths.get("LocalSocket"):
        cfg.socket = Path(v)
    if v := paths.get("LogFile"):
        cfg.log_file = Path(v)
    if v := paths.get("DatabaseDirectory"):
        cfg.database_dir = Path(v)
    cfg.scan_log = _guess_scan_log(cfg.log_file)

    if CONFIG_PATH.is_file():
        try:
            data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        _apply_overrides(cfg, data)

    return cfg


def _apply_overrides(cfg: Config, data: dict) -> None:
    general = data.get("general", {})
    if v := general.get("refresh_secs"):
        cfg.refresh_secs = int(v)
    if v := general.get("terminal"):
        cfg.terminal = str(v)

    paths = data.get("paths", {})
    for key, attr in (
        ("socket", "socket"),
        ("log_file", "log_file"),
        ("scan_log", "scan_log"),
        ("quarantine", "quarantine"),
        ("database_dir", "database_dir"),
    ):
        if v := paths.get(key):
            setattr(cfg, attr, Path(v).expanduser())

    units = data.get("units", {})
    if v := units.get("watch"):
        cfg.units = list(v)
    if v := units.get("labels"):
        cfg.labels = dict(v)


# O clamconf so conhece o log do daemon. O resumo da varredura vai para onde quer
# que o agendamento tenha mandado, e isso e escolha de quem configurou a maquina.
# Estes nomes cobrem a convencao mais comum; o resto e `paths.scan_log` no TOML.
_SCAN_LOG_NAMES = ("scan.log", "clamav-scan.log", "clamdscan.log", "daily-scan.log")


def _guess_scan_log(daemon_log: Path | None) -> Path | None:
    """Procura um log de varredura ao lado do log do daemon.

    Heuristica deliberadamente curta: acertar o caso comum sem exigir config, e
    devolver None (nao um palpite errado) quando nao houver certeza. O tray sabe
    lidar com None; o que ele nao sabe e lidar com o arquivo errado.
    """
    if daemon_log is None:
        return None
    for name in _SCAN_LOG_NAMES:
        candidate = daemon_log.parent / name
        if candidate.is_file():
            return candidate
    return None
