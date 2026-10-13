"""Testes do autostart: o arquivo que vai rodar a cada login.

O caso que motivou o modulo: a unidade apontava para ~/.local/bin/clamav-tray
mesmo rodando do codigo-fonte, e o servico entrava em laco com 203/EXEC. Aqui se
confere que o ExecStart e o diretorio de trabalho saem do que foi resolvido, e
que --show-autostart mostra a DIFERENCA quando ja existe arquivo.
"""

import os
import tempfile
from pathlib import Path

from clamav_tray import autostart


def test_unidade_usa_o_exec_resolvido_e_nao_o_do_modelo():
    txt = autostart.render("systemd", "/opt/bin/clamav-tray", None)
    assert "ExecStart=/opt/bin/clamav-tray\n" in txt
    assert "%h/.local/bin" not in txt
    assert "WorkingDirectory" not in txt
    assert "Restart=always" in txt


def test_codigo_fonte_ganha_diretorio_de_trabalho_logo_apos_service():
    txt = autostart.render("systemd", "/usr/bin/python3 -m clamav_tray", Path("/src/clamav-tray"))
    linhas = txt.splitlines()
    i = linhas.index("[Service]")
    assert linhas[i + 1] == "WorkingDirectory=/src/clamav-tray"
    assert "ExecStart=/usr/bin/python3 -m clamav_tray" in linhas


def test_desktop_xdg():
    txt = autostart.render("xdg", "/opt/bin/clamav-tray", None)
    assert "Exec=/opt/bin/clamav-tray\n" in txt
    assert txt.count("Exec=") == 1
    assert "[Desktop Entry]" in txt


def test_modelos_estao_no_pacote():
    # Se o package-data do pyproject se perder, o PyPI volta a entregar um
    # programa que nao consegue instalar o proprio autostart.
    for nome in (autostart.UNIT_NAME, autostart.DESKTOP_NAME):
        assert autostart.files("clamav_tray").joinpath("data", nome).is_file()


def _com_config_temporaria(fn):
    antes = os.environ.get("XDG_CONFIG_HOME")
    with tempfile.TemporaryDirectory() as d:
        os.environ["XDG_CONFIG_HOME"] = d
        try:
            return fn(Path(d))
        finally:
            if antes is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = antes


def test_show_sem_arquivo_mostra_conteudo_e_destino():
    def caso(raiz):
        p = autostart.plan("xdg")
        assert p.dest == raiz / "autostart" / "clamav-tray.desktop"
        texto = autostart.describe(p)
        assert str(p.dest) in texto
        assert "Conteudo que seria gravado" in texto
        assert not p.dest.exists()  # mostrar nunca grava
    _com_config_temporaria(caso)


def test_show_com_arquivo_diferente_mostra_diff():
    def caso(raiz):
        p = autostart.plan("xdg")
        p.dest.parent.mkdir(parents=True)
        p.dest.write_text(p.content.replace("Exec=", "Exec=/caminho/antigo #"))
        texto = autostart.describe(p)
        assert "JA EXISTE" in texto
        assert "-Exec=/caminho/antigo" in texto
        assert f"+Exec={p.exec_line}" in texto
    _com_config_temporaria(caso)


def test_show_com_arquivo_identico():
    def caso(raiz):
        p = autostart.plan("xdg")
        p.dest.parent.mkdir(parents=True)
        p.dest.write_text(p.content)
        assert "identico" in autostart.describe(p)
    _com_config_temporaria(caso)


def test_sem_terminal_e_sem_yes_nao_grava():
    def caso(raiz):
        import io
        import sys
        stdin, sys.stdin = sys.stdin, io.StringIO("")
        try:
            assert autostart.install("xdg", yes=False) == 1
        finally:
            sys.stdin = stdin
        assert not (raiz / "autostart" / "clamav-tray.desktop").exists()
    _com_config_temporaria(caso)


def test_xdg_com_yes_grava_e_desinstala():
    def caso(raiz):
        dest = raiz / "autostart" / "clamav-tray.desktop"
        assert autostart.install("xdg", yes=True) == 0
        assert dest.read_text() == autostart.plan("xdg").content
        assert oct(dest.stat().st_mode & 0o777) == "0o644"
        assert autostart.uninstall("xdg", yes=True) == 0
        assert not dest.exists()
    _com_config_temporaria(caso)
