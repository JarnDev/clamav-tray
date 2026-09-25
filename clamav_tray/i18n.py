"""Traducao.

Nao usa gettext de proposito. gettext exige compilar .po em .mo, o que
acrescenta um passo de build a um projeto que hoje instala com `pipx install` e
nada mais. Para um catalogo desta ordem de grandeza, um dicionario Python e
honesto: quem quiser traduzir copia um bloco e traduz, sem instalar ferramenta.

Se o catalogo crescer a ponto de isso doer, a migracao para gettext e mecanica —
as chaves JA sao as frases em ingles, que e exatamente o que o gettext espera.

O INGLES E A FONTE. As strings no codigo estao em ingles e nao passam por
traducao quando o idioma e `en`; traduzir e opcional por construcao, e uma chave
sem traducao aparece em ingles em vez de quebrar.
"""

from __future__ import annotations

import os

DEFAULT = "en"

CATALOGS: dict[str, dict[str, str]] = {
    "pt_BR": {
        # Cabecalho
        "Protected": "Protegido",
        "all services running": "todos os serviços no ar",
        "Scanning": "Varredura em andamento",
        "Attention": "Atenção",
        "Threat detected": "Ameaça detectada",
        "{n} file(s) quarantined": "{n} arquivo(s) em quarentena",
        "{names} not healthy": "{names} com problema",
        "and {n} more": "e mais {n}",
        # Secoes
        "Scan": "Varredura",
        "Services": "Serviços",
        # Linhas
        "In progress": "Em andamento",
        "Files": "Arquivos",
        "Remaining": "Faltam",
        "Rate": "Ritmo",
        "{n}/s": "{n}/s",
        "Elapsed": "Decorrido",
        "Infected": "Infectados",
        "none so far": "nenhum até agora",
        "Target": "Alvo",
        "Moves to": "Move para",
        "Source": "Origem",
        "started outside the tray": "iniciada fora do tray",
        "Last": "Última",
        "Next": "Próxima",
        "History": "Histórico",
        "Quarantine": "Quarentena",
        "Quarantine (mine)": "Quarentena (minha)",
        "empty": "vazia",
        "{n} file": "{n} arquivo",
        "{n} files": "{n} arquivos",
        "needs root to list": "precisa de root para listar",
        "unavailable": "indisponível",
        "no journal access (group adm or systemd-journal)":
            "sem acesso ao journal (grupo adm ou systemd-journal)",
        "for {duration}": "há {duration}",
        "estimate {duration}": "estimativa {duration}",
        # Veredito
        "no result recorded": "sem resultado registrado",
        "scan did not finish": "a varredura não concluiu",
        "clean": "limpa",
        "{n} threat found": "{n} ameaça encontrada",
        "{n} threats found": "{n} ameaças encontradas",
        "{n} unreadable file": "{n} arquivo ilegível",
        "{n} unreadable files": "{n} arquivos ilegíveis",
        # Acoes
        "Scan my home now": "Varrer minha home agora",
        "Stop scan": "Parar varredura",
        "List quarantine": "Listar quarentena",
        "View logs": "Ver logs",
        "Settings": "Configurações",
        "Quit": "Sair",
        # Datas
        "today": "hoje",
        "yesterday": "ontem",
        "tomorrow": "amanhã",
    },
}

_active: dict[str, str] = {}


def set_language(code: str | None) -> str:
    """Define o idioma. `auto` segue o ambiente; qualquer outro valor desconhecido
    cai em ingles, em vez de falhar."""
    global _active
    if code == "auto":
        code = _from_environment()
    code = code or DEFAULT
    _active = CATALOGS.get(code, {})
    return code if code in CATALOGS or code == DEFAULT else DEFAULT


def _from_environment() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if value := os.environ.get(var):
            tag = value.split(".")[0].split("@")[0]
            if tag in CATALOGS:
                return tag
            # pt_PT cai em pt_BR: traducao parcialmente errada e melhor que ingles
            # para quem nao le ingles, e nao ha catalogo pt_PT.
            base = tag.split("_")[0]
            for known in CATALOGS:
                if known.split("_")[0] == base:
                    return known
    return DEFAULT


def _(text: str, **kwargs) -> str:
    """Traduz e interpola. Chave ausente devolve o ingles."""
    out = _active.get(text, text)
    return out.format(**kwargs) if kwargs else out


def available() -> list[str]:
    return [DEFAULT, *CATALOGS]
