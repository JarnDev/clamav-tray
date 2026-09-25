"""De onde vem o texto do ultimo SCAN SUMMARY.

Faz parte do modulo 2 da migracao (o lado de I/O). A interpretacao do texto mora em
scan.py, que continua puro — aqui so se busca.

Duas fontes, nesta ordem:

1. o arquivo de log, quando existe e e legivel
2. o journal da unidade

A segunda costuma exigir grupo `adm` ou `systemd-journal`, e a falta disso NAO pode
derrubar o programa: sem historico, o indicador ainda mostra o estado atual. Um
indicador que some porque nao pode ler o passado e pior que um que admite nao saber.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Um SCAN SUMMARY tem poucas dezenas de linhas, mas vem depois de uma lista de
# ERROR que pode ser longa. 400 KB cobre com folga sem carregar log de meses.
_TAIL_BYTES = 400_000


def from_log_file(path: Path | None) -> str | None:
    if not path or not path.is_file():
        return None
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - _TAIL_BYTES))
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def from_journal(unit_id: str, lines: int = 400, user: bool = False) -> str | None:
    """`user=True` le o journal do USUARIO, onde cai a varredura sob demanda
    lancada com `systemd-run --user`. Esse journal nao exige grupo nenhum: e seu."""
    try:
        proc = subprocess.run(
            ["journalctl", *(["--user"] if user else []),
             "-u", unit_id, "-n", str(lines), "--no-pager", "-o", "cat"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # Sem permissao, o journalctl responde vazio ou so com aviso; texto vazio e
    # tratado como "nao sei", nao como "limpo".
    return proc.stdout or None


def last_summary(
    log_file: Path | None,
    unit_id: str | None,
    user: bool = False,
    output: Path | None = None,
) -> str | None:
    """Ultimo trecho que possa conter um SCAN SUMMARY, da fonte que responder.

    `output` vem PRIMEIRO quando dado. E o arquivo para onde a varredura sob
    demanda redireciona a saida — redirecionamento que existe para a barra de
    progresso poder contar linhas.

    Sem este parametro havia um buraco silencioso: desde que a saida passou a ir
    para arquivo, o journal da unidade ficou vazio, e o tray caia no log da
    varredura AGENDADA. Uma ameaca encontrada sob demanda nao acendia o icone —
    ele mostrava, tranquilo, o veredito de outra varredura.
    """
    if output and (text := from_log_file(output)):
        return _tail_after_last_summary(text)
    if user and unit_id and (text := from_journal(unit_id, user=True)):
        return _tail_after_last_summary(text)
    if text := from_log_file(log_file):
        return _tail_after_last_summary(text)
    if unit_id and (text := from_journal(unit_id)):
        return _tail_after_last_summary(text)
    return None


def _tail_after_last_summary(text: str) -> str:
    """Corta tudo antes do ultimo 'SCAN SUMMARY'.

    O log e acumulado: sem este corte, um 'Infected files: 1' de tres semanas atras
    seria lido como se fosse de hoje.
    """
    marker = "SCAN SUMMARY"
    idx = text.rfind(marker)
    return text if idx < 0 else text[idx:]


def journal_readable() -> bool:
    """Se da para ler journal de unidade do sistema. Usado so para explicar ao
    usuario por que o historico esta faltando, em vez de deixar o campo vazio."""
    try:
        proc = subprocess.run(
            ["journalctl", "-n", "1", "--no-pager", "-u", "init.scope"],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False
