"""Estado das unidades do systemd.

Modulo 2 da migracao. Ainda sincrono, mas ja fala com o mundo.

Duas decisoes que carregam o modulo inteiro:

1. UMA chamada ao systemctl para TODAS as unidades, nao uma por unidade. O script
   original gastava 4 processos a cada 10s — ~34 mil por dia, so para ler quatro
   strings.

2. A ordem dos campos na saida do `systemctl show` NAO e estavel: `Id` aparece em
   posicoes diferentes entre blocos. Por isso o parser monta dicionario e nunca
   confia em posicao. Chave ausente e normal (um `.timer` nao tem `Type`).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

PROPS = [
    "Id", "Type", "ActiveState", "SubState", "Result",
    "ExecMainStartTimestamp", "ExecMainExitTimestamp", "InactiveEnterTimestamp",
    "NextElapseUSecRealtime", "LastTriggerUSec",
]


class Kind(Enum):
    DAEMON = "daemon"
    """Fica no ar de proposito. Rodando = saudavel."""

    JOB = "job"
    """Roda e termina. Rodando = EM EXECUCAO agora."""

    TIMER = "timer"
    """Agenda outra unidade. Esperando = saudavel."""


@dataclass(frozen=True)
class Unit:
    id: str
    kind: Kind
    active_state: str
    sub_state: str
    result: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    next_elapse: datetime | None = None
    user_scope: bool = False
    """Unidade do barramento do usuario (`systemctl --user`). A varredura sob
    demanda vive la: `clamdscan --fdpass` nao precisa de root, porque quem abre os
    arquivos e o proprio usuario."""

    @property
    def is_running_job(self) -> bool:
        """Tarefa em execucao AGORA.

        Sem a distincao por `kind`, um monitor de pasta (que fica `active running`
        para sempre) seria lido como "varredura em andamento" eternamente.
        """
        # `exited` e a marca de "terminou mas a unidade ficou" (--remain-after-exit).
        # Sem esta excecao a varredura sob demanda apareceria como eterna.
        if self.sub_state == "exited":
            return False
        return self.kind is Kind.JOB and self.active_state in ("activating", "active")

    @property
    def is_healthy(self) -> bool:
        if self.kind is Kind.DAEMON:
            return self.active_state == "active"
        if self.kind is Kind.TIMER:
            return self.active_state == "active"
        # Tarefa: falhou de verdade so quando o systemd diz que falhou. O veredito
        # da varredura em si vem do SCAN SUMMARY, nao daqui — ver scan.py.
        return self.active_state != "failed"

    @property
    def elapsed_secs(self) -> int | None:
        if self.started_at is None:
            return None
        return int((datetime.now(timezone.utc) - self.started_at).total_seconds())


# Prefixo das unidades transitorias que ESTE programa cria com systemd-run.
TRANSIENT_PREFIX = "clamav-tray-scan"


def _classify(unit_id: str, type_: str) -> Kind:
    if unit_id.endswith(".timer"):
        return Kind.TIMER
    # Unidade criada pelo systemd-run nao declara Type, entao cairia em DAEMON e
    # seria lida como "servico no ar" em vez de "varredura rodando". Como o nome e
    # nosso, a regra e explicita.
    if unit_id.startswith(TRANSIENT_PREFIX):
        return Kind.JOB
    # `oneshot` e a assinatura de "roda e termina". `simple`/`notify`/`forking`
    # descrevem processo que fica de pe.
    return Kind.JOB if type_ == "oneshot" else Kind.DAEMON


def _parse_ts(value: str) -> datetime | None:
    """systemd imprime 'Fri 2026-09-25 03:09:23 -03'. Duas armadilhas:

    1. O nome do dia depende do LOCALE — "Fri" em C, "sex" em pt_BR. Por isso ele e
       DESCARTADO em vez de casado: a data completa ja esta no resto da string.
    2. O fuso sai com DOIS digitos ("-03") em varios fusos, e o %z do Python exige
       quatro ("-0300"). Foi o que fez finished_at e next_elapse virarem None, e as
       linhas "Ultima" e "Proxima" aparecerem vazias.
    """
    value = value.strip()
    if not value or value in ("n/a", "0"):
        return None

    parts = value.split()
    # Descarta o dia da semana, se houver: comeca com letra, nao com digito.
    if parts and not parts[0][0].isdigit():
        parts = parts[1:]
    if len(parts) < 2:
        return None

    stamp = " ".join(parts[:2])
    tz = parts[2] if len(parts) > 2 else ""
    if tz:
        sign, digits = tz[0], tz[1:].replace(":", "")
        if sign in "+-" and digits.isdigit():
            tz = f"{sign}{digits.ljust(4, '0')}"   # -03 -> -0300
        else:
            tz = ""   # nome de fuso ("UTC", "-03" abreviado) nao e offset

    candidates = []
    if tz:
        candidates.append((f"{stamp} {tz}", "%Y-%m-%d %H:%M:%S %z"))
    candidates.append((stamp, "%Y-%m-%d %H:%M:%S"))

    for text, fmt in candidates:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        # Sem fuso na string, assume-se o local — que e o que o systemd imprimiu.
        return parsed if parsed.tzinfo else parsed.astimezone()
    return None


def _systemctl(user: bool, *args: str) -> list[str]:
    return ["systemctl", *(["--user"] if user else []), *args]


def discover(glob: str = "clam*", user: bool = False) -> list[str]:
    """Nomes de unidade existentes.

    O glob e o que torna o programa portavel sem configuracao: pega
    `clamav-daemon.service` (Debian, Ubuntu, Arch) e `clamd@scan.service`
    (Fedora, que usa unidade templated) com a mesma regra.
    """
    out = _run(_systemctl(user, "list-units", "--all", "--no-pager", "--no-legend", glob))
    ids = []
    for line in out.splitlines():
        for field in line.split():
            if field.endswith((".service", ".timer", ".socket", ".path")):
                ids.append(field)
                break
    return ids


def query(unit_ids: list[str], user: bool = False) -> dict[str, Unit]:
    """Estado de varias unidades em UMA chamada."""
    if not unit_ids:
        return {}
    out = _run(_systemctl(user, "show", "-p", ",".join(PROPS), *unit_ids))

    units: dict[str, Unit] = {}
    for block in out.split("\n\n"):
        fields = dict(
            line.split("=", 1) for line in block.splitlines() if "=" in line
        )
        unit_id = fields.get("Id")
        if not unit_id:
            continue
        units[unit_id] = Unit(
            id=unit_id,
            kind=_classify(unit_id, fields.get("Type", "")),
            user_scope=user,
            active_state=fields.get("ActiveState", "unknown"),
            sub_state=fields.get("SubState", "unknown"),
            result=fields.get("Result", "unknown"),
            started_at=_parse_ts(fields.get("ExecMainStartTimestamp", "")),
            # ExecMainExit vem PRIMEIRO: com --remain-after-exit a unidade fica
            # `active/exited` e NUNCA entra em inactive, entao
            # InactiveEnterTimestamp permanece vazio. Ler so ele fazia o horario
            # de termino sumir justamente nas varreduras sob demanda.
            finished_at=(_parse_ts(fields.get("ExecMainExitTimestamp", ""))
                         or _parse_ts(fields.get("InactiveEnterTimestamp", ""))),
            next_elapse=_parse_ts(fields.get("NextElapseUSecRealtime", "")),
        )
    return units


def _run(argv: list[str]) -> str:
    """systemctl sai com codigo != 0 em varias situacoes normais (unidade falhada,
    inexistente). O texto vem junto, entao nunca levantamos por causa disso."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        return proc.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def query_all(system_ids: list[str]) -> dict[str, Unit]:
    """Junta os dois barramentos.

    As unidades do ClamAV instaladas pela distro vivem no barramento do SISTEMA.
    A varredura sob demanda que este programa lanca vive no do USUARIO, porque
    `clamdscan --fdpass` nao precisa de root — quem abre os arquivos e voce.

    Consultar so um dos dois deixa o botao "varrer agora" invisivel para o
    indicador, que foi exatamente o sintoma relatado.
    """
    merged = query(system_ids)
    transient = [u for u in discover(f"{TRANSIENT_PREFIX}*", user=True)]
    if transient:
        merged.update(query(transient, user=True))
    return merged


def scan_process_running() -> bool:
    """Rede de seguranca: qualquer clamdscan/clamscan do usuario, venha de onde vier.

    Cobre varredura lancada fora do tray — terminal, cron, outro programa. Nao da
    para ler o resultado dela, mas dizer "esta varrendo" ja evita que o indicador
    afirme calmaria enquanto o disco arde.
    """
    try:
        proc = subprocess.run(
            ["pgrep", "-u", str(os.getuid()), "-x", "clamdscan,clamscan"],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def pick_scan_unit(state: dict[str, Unit]) -> Unit | None:
    """Qual tarefa representa "a varredura" na interface.

    A sob demanda (barramento do usuario) tem precedencia sobre a agendada: e a
    mais recente e e a que a pessoa acabou de pedir.

    Mora aqui, e nao na camada grafica, porque e regra sobre unidades — e porque
    ja houve divergencia: o modo --dump reimplementou com um `next()` que pegava a
    primeira do dicionario e mostrava o resultado errado.
    """
    jobs = [u for u in state.values() if u.kind is Kind.JOB]
    if not jobs:
        return None
    jobs.sort(key=lambda u: (not u.user_scope, u.id))
    return jobs[0]
