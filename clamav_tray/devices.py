"""Midia removivel montada e acessivel a este usuario.

Nao usa `lsblk`: um subprocesso a cada atualizacao do menu e o erro que este
projeto ja pagou uma vez — o script de origem gastava ~34 mil processos por dia
so para ler quatro strings. Aqui sao duas leituras de arquivo.

Como a deteccao funciona:

1. `/proc/mounts` diz o que esta montado e onde.
2. `/sys/block/<disco>/removable` diz se o hardware e removivel. E o dado do
   kernel, nao heuristica.

O filtro por `/media/$USER` e `/run/media/$USER` sozinho seria PROXY: e onde o
udisks2 monta, mas alguem pode montar disco fixo ali. Por isso o cruzamento.

LIMITE CONHECIDO: midia que o usuario nunca abriu nao esta montada, e o que nao
esta montado nao pode ser varrido por um processo de usuario. Esse caso so o
caminho com root cobre — ver contrib/extras/usb-scan.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

MOUNT_PREFIXES = ("/media/", "/run/media/")

# sdc1 -> sdc ; nvme0n1p3 -> nvme0n1 ; mmcblk0p1 -> mmcblk0
_BASE = re.compile(r"^(nvme\d+n\d+|mmcblk\d+|sd[a-z]+|hd[a-z]+)")


@dataclass(frozen=True)
class Device:
    source: str
    """Caminho do dispositivo, ex.: /dev/sdc1."""
    mountpoint: Path
    label: str
    size_bytes: int | None = None

    @property
    def key(self) -> str:
        """Identidade estavel o bastante para lembrar se ja foi varrido.

        Ponto de montagem sozinho nao serve: dois pendrives com o mesmo rotulo
        montam no mesmo caminho em momentos diferentes.
        """
        return f"{self.source}:{self.mountpoint}"


def _unescape(value: str) -> str:
    """/proc/mounts escapa espaco como \\040 e afins."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), value)


def _is_removable(source: str) -> bool:
    name = os.path.basename(source)
    m = _BASE.match(name)
    if not m:
        return False
    try:
        return Path(f"/sys/block/{m.group(1)}/removable").read_text().strip() == "1"
    except OSError:
        return False


def _size(mountpoint: Path) -> int | None:
    try:
        st = os.statvfs(mountpoint)
        return st.f_blocks * st.f_frsize
    except OSError:
        return None


def list_removable() -> list[Device]:
    """Midia removivel montada sob a arvore do usuario."""
    try:
        raw = Path("/proc/mounts").read_text(errors="replace")
    except OSError:
        return []

    user = os.environ.get("USER") or ""
    out: list[Device] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        source, mountpoint = _unescape(parts[0]), _unescape(parts[1])
        if not source.startswith("/dev/"):
            continue
        if not any(mountpoint.startswith(p) for p in MOUNT_PREFIXES):
            continue
        # Restringe ao que e nosso: /media/outro-usuario nao nos interessa e
        # provavelmente nem e legivel.
        if user and f"/{user}/" not in mountpoint + "/":
            continue
        if not _is_removable(source):
            continue
        path = Path(mountpoint)
        out.append(Device(
            source=source, mountpoint=path, label=path.name, size_bytes=_size(path)))
    return out


def human_size(n: int | None) -> str:
    if not n:
        return ""
    for unit, div in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2)):
        if n >= div:
            return f"{n / div:.1f} {unit}".replace(".0 ", " ").replace(".", ",")
    return f"{n // 1024} KB"
