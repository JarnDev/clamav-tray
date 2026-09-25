"""Testes do modulo 1 — o primeiro a ser portado para Rust.

Estes casos sao o CONTRATO. A versao em Rust tem de passar pelos mesmos, com as
mesmas entradas. Por isso as amostras sao saida real de clamdscan, colada como
esta, e nao texto inventado: o valor do teste esta em ele ter vindo de uma
maquina de verdade.
"""

from clamav_tray.scan import Verdict, describe, human_duration, parse_summary

# Saida real de uma varredura de 4h33 em 1.099.137 arquivos. Os seis erros sao
# arquivos que sumiram durante a varredura (IndexedDB do Slack, backup rotativo)
# mais um PDF cujo NOME contem uma quebra de linha, o que quebra --file-list.
REAL_CLEAN_WITH_ERRORS = """\
ERROR: Can't access file /home/u/.var/app/com.slack.Slack/config/Slack/IndexedDB/2/64/64f3
ERROR: Can't access file /home/u/Documents/1.ByteByteGo _Join the Community
ERROR: Can't access file /.pdf

----------- SCAN SUMMARY -----------
Infected files: 0
Total errors: 6
Time: 16317.863 sec (271 m 57 s)
Start Date: 2026:09:25 03:10:31
End Date:   2026:09:25 07:42:29
"""

REAL_INFECTED = """\
/home/u/Downloads/eicar.com: Win.Test.EICAR_HDB-1 FOUND

----------- SCAN SUMMARY -----------
Scanned files: 12
Infected files: 1
Total errors: 0
Time: 3.100 sec (0 m 3 s)
"""


def test_clean_apesar_de_erros():
    """O caso que motivou o projeto.

    A unidade do systemd sai com codigo 2 por causa dos erros de acesso, e por isso
    aparece como `failed`. Nao ha ameaca nenhuma. Se o indicador acreditasse no
    codigo de saida, ele gritaria todos os dias — e um alarme que sempre toca
    deixa de ser alarme.
    """
    r = parse_summary(REAL_CLEAN_WITH_ERRORS)
    assert r.verdict is Verdict.CLEAN
    assert r.infected == 0
    assert r.unreadable == 6
    assert r.is_alarming is False


def test_infectado_e_alarme():
    r = parse_summary(REAL_INFECTED)
    assert r.verdict is Verdict.INFECTED
    assert r.infected == 1
    assert r.is_alarming is True


def test_sem_resumo_e_desconhecido_nao_limpo():
    """Nao saber e diferente de estar limpo. Se o log ainda nao tem resumo, o
    indicador precisa dizer que nao sabe, nunca inventar um zero tranquilizador."""
    r = parse_summary("Starting scan...\nnada aqui\n")
    assert r.verdict is Verdict.UNKNOWN
    assert r.is_alarming is False


def test_resumo_com_lixo_em_volta():
    """Log acumulado: o parser tem de achar o resumo no meio do ruido."""
    noisy = "linha velha\n" * 500 + REAL_INFECTED + "\nrodape irrelevante\n"
    assert parse_summary(noisy).infected == 1


def test_duracao_lida_do_resumo():
    assert parse_summary(REAL_CLEAN_WITH_ERRORS).duration_secs == 16317


def test_descricao_menciona_ilegiveis_sem_alarmar():
    texto = describe(parse_summary(REAL_CLEAN_WITH_ERRORS))
    assert "limpa" in texto
    assert "6 arquivos ilegiveis" in texto


def test_descricao_de_ameaca():
    assert "1 ameaca encontrada" in describe(parse_summary(REAL_INFECTED))


def test_duracao_usa_a_unidade_mais_grossa_que_informa():
    assert human_duration(45) == "45s"
    assert human_duration(720) == "12m"
    assert human_duration(16317) == "4h31"
