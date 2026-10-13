"""Formato de numero por idioma.

Regressao: a interface em ingles mostrava "14,9 GB" e "1.131.791" — cada modulo
trocava ponto por virgula por conta propria, sem olhar o idioma.
"""

from clamav_tray import devices, quarantine
from clamav_tray.i18n import number, set_language


def test_numero_em_ingles_e_portugues():
    set_language("en")
    assert number(1131791) == "1,131,791"
    assert number(14.94, 1) == "14.9"
    assert number(1234.5, 1) == "1,234.5"
    set_language("pt_BR")
    assert number(1131791) == "1.131.791"
    assert number(14.94, 1) == "14,9"
    assert number(1234.5, 1) == "1.234,5"
    set_language("en")


def test_tamanhos_seguem_o_idioma():
    pen = int(14.9 * 1024 ** 3)
    set_language("en")
    assert devices.human_size(pen) == "14.9 GB"
    assert devices.human_size(16 * 1024 ** 3) == "16 GB"
    assert quarantine.human_bytes(2178432) == "2.1 MB"
    set_language("pt_BR")
    assert devices.human_size(pen) == "14,9 GB"
    assert devices.human_size(16 * 1024 ** 3) == "16 GB"
    assert quarantine.human_bytes(2178432) == "2,1 MB"
    set_language("en")


def test_idioma_desconhecido_cai_no_ingles():
    set_language("xx_YY")
    assert number(1234.5, 1) == "1,234.5"
    set_language("en")
