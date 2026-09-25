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
    "clamav-tray-daily.service": "Daily scan",
    "clamav-tray-downloads.service": "Downloads watcher",
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
    """Quarentena do SISTEMA, onde a varredura agendada (root) move. Normalmente
    ilegivel para o usuario, e isso esta certo."""
    user_quarantine: Path | None = None
    """Quarentena do USUARIO, usada pela varredura sob demanda. Ver _user_quarantine."""
    units: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    refresh_secs: int = 10
    terminal: str | None = None
    language: str = "en"
    """Ingles e o padrao. "auto" segue o ambiente; "pt_BR" forca o portugues."""
    loaded_from_mtime: float | None = None
    """Para o tray perceber que o arquivo mudou e recarregar sozinho."""

    def label_for(self, unit_id: str) -> str:
        if unit_id in self.labels:
            return self.labels[unit_id]
        if unit_id in KNOWN_LABELS:
            return KNOWN_LABELS[unit_id]
        # Unidade templated: clamav-tray-usb@sdc1.service -> "Usb (sdc1)". Sem
        # isto o rotulo sairia com o @ cru, que nao diz nada a quem olha a bandeja.
        stem = unit_id.rsplit(".", 1)[0]
        if "@" in stem:
            base, _, instance = stem.partition("@")
            base = re.sub(r"^clamav?-(tray-)?", "", base).replace("-", " ")
            return f"{base.title()} ({instance})" if instance else base.title()
        stem = re.sub(r"^clamav?-(tray-)?", "", stem).replace("-", " ").replace("_", " ")
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
    cfg.quarantine = _guess_quarantine()
    cfg.user_quarantine = _user_quarantine()

    if CONFIG_PATH.is_file():
        try:
            data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        _apply_overrides(cfg, data)
        try:
            cfg.loaded_from_mtime = CONFIG_PATH.stat().st_mtime
        except OSError:
            pass

    return cfg


def _apply_overrides(cfg: Config, data: dict) -> None:
    general = data.get("general", {})
    if v := general.get("refresh_secs"):
        cfg.refresh_secs = int(v)
    if v := general.get("terminal"):
        cfg.terminal = str(v)
    if v := general.get("language"):
        cfg.language = str(v)

    paths = data.get("paths", {})
    for key, attr in (
        ("socket", "socket"),
        ("log_file", "log_file"),
        ("scan_log", "scan_log"),
        ("quarantine", "quarantine"),
        ("user_quarantine", "user_quarantine"),
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


TEMPLATE = """\
# clamav-tray — all settings are optional.
# Without this file the program discovers units via the `clam*` glob and paths
# via `clamconf`. Changes are picked up automatically, no restart needed.

[general]
# "en" (default), "pt_BR", or "auto" to follow the system locale.
language = "en"
refresh_secs = 10
# terminal = "kitty"     # default: autodetect

[paths]
# clamconf knows the DAEMON socket and log. It does NOT know where your scan
# writes — that depends on how you scheduled it. If the menu says "no result
# recorded", this is the missing field.
# scan_log   = "/var/log/clamav/scan.log"
# quarantine = "/var/quarantine/clamav"

[units]
# The `clam*` glob finds everything, including Fedora's clamd@scan.service.
# Set this only to restrict, or to add a unit named outside the convention.
# watch = ["clamav-daemon.service", "clamav-freshclam.service"]

[units.labels]
# "clamav-scan-downloads.service" = "Downloads Monitor"
"""


def ensure_file() -> Path:
    """Garante que o arquivo exista, para o item Settings ter o que abrir.

    Escrever um modelo COMENTADO em vez de despejar a configuracao efetiva e
    deliberado: o usuario precisa ver quais chaves existem, nao um retrato dos
    valores que o programa descobriu sozinho — esses mudam de maquina para
    maquina e copiá-los engessaria a deteccao automatica.
    """
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(TEMPLATE, encoding="utf-8")
    return CONFIG_PATH


def changed_on_disk(cfg: Config) -> bool:
    try:
        return CONFIG_PATH.stat().st_mtime != cfg.loaded_from_mtime
    except OSError:
        return cfg.loaded_from_mtime is not None


# O clamconf nao conhece quarentena: ela nasce do `--move=` de quem agendou a
# varredura, nao da configuracao do ClamAV. Nao ha caminho padrao na especificacao;
# estes sao os que aparecem na pratica.
_QUARANTINE_PATHS = (
    "/var/quarantine/clamav",
    "/var/lib/clamav/quarantine",
    "/var/spool/clamav/quarantine",
)


def _guess_quarantine() -> Path | None:
    """Acha a quarentena por caminho conhecido.

    `is_dir()` responde True mesmo sem permissao de LEITURA, o que e o que
    queremos: o diretorio existir ja justifica mostrar a linha no menu. Se dara
    para listar o conteudo e outra questao, decidida na hora de mostrar.
    """
    for candidate in _QUARANTINE_PATHS:
        path = Path(candidate)
        try:
            if path.is_dir():
                return path
        except OSError:
            continue
    return None


# O clamdscan cria uma trava por execucao dentro da quarentena e NAO a remove
# quando a varredura e interrompida. Conta-las como conteudo transforma o
# indicador em alarme falso: seis travas viraram "6 arquivos" em laranja, sem
# nenhuma deteccao ter acontecido.
LOCK_PREFIX = ".clamav-quarantine-lock"


def is_lock(path: Path) -> bool:
    return path.name.startswith(LOCK_PREFIX)


def clean_stale_locks(path: Path | None) -> int:
    """Remove travas de processos que nao existem mais.

    So apaga o que casa com o prefixo E cujo PID morreu — nunca toca em arquivo
    de conteudo. O PID esta no proprio nome: .clamav-quarantine-lock.<pid>.<n>
    """
    if path is None or not path.is_dir():
        return 0
    removed = 0
    for entry in path.iterdir():
        if not is_lock(entry):
            continue
        parts = entry.name.split(".")
        pid = next((int(x) for x in parts if x.isdigit()), None)
        if pid is None or Path(f"/proc/{pid}").exists():
            continue
        try:
            entry.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def quarantine_count(path: Path | None) -> int | None:
    """Quantos arquivos ha na quarentena, ou None se nao der para ler.

    None NAO e zero. Quarentena costuma ser `750` dono root de proposito — e
    malware guardado — entao nao poder contar e o caso NORMAL, nao erro.
    """
    if path is None:
        return None
    try:
        return sum(1 for entry in path.iterdir() if not is_lock(entry))
    except OSError:
        return None


def _user_quarantine() -> Path:
    """Quarentena que a varredura sob demanda consegue usar.

    POR QUE existir uma segunda: a varredura sob demanda roda como o usuario, e a
    quarentena do sistema e 750 dono root. Sem um destino gravavel, o `--move` nao
    podia ser usado e a varredura so detectava — o arquivo malicioso continuava
    exatamente onde estava, que e o pior dos mundos.

    POR QUE isto nao enfraquece nada: o arquivo ja estava na home do usuario, com
    as permissoes dele. Move-lo para ca nao aumenta privilegio — DIMINUI exposicao,
    porque sai do lugar onde poderia ser aberto por engano e vai para um diretorio
    que nenhum programa varre, indexa ou gera miniatura.

    Modo 0700: nem outros usuarios da maquina alcancam.
    """
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "clamav-tray" / "quarantine"


def ensure_user_quarantine(path: Path) -> Path | None:
    """Cria sob demanda. Nao e criada na inicializacao de proposito: diretorio
    vazio que nunca sera usado e sujeira."""
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path
    except OSError:
        return None
