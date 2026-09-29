"""Testes da escolha de unidade — modulo 2 da migracao.

O caso central aqui e uma REGRESSAO com data e hora: em 29/09/2026 o indicador
estava vermelho anunciando ameaca, com tres varreduras agendadas limpas depois do
achado. Os valores abaixo sao os da maquina onde isso aconteceu, copiados do
`systemctl show`, e nao numeros inventados: o valor do teste esta em ele descrever
um estado que existiu.
"""

from datetime import datetime, timedelta, timezone

from clamav_tray.units import Kind, Unit, pick_full_scan_unit, pick_scan_unit

TZ = timezone(timedelta(hours=-3))


def _job(unit_id, *, user, finished, status=0, active="inactive", sub="dead"):
    return Unit(
        id=unit_id,
        kind=Kind.JOB,
        user_scope=user,
        active_state=active,
        sub_state=sub,
        result="success" if status == 0 else "exit-code",
        exit_status=status,
        finished_at=finished,
    )


# A transitoria de 25/09 achou o EICAR de um teste e ficou `failed` para sempre:
# --remain-after-exit guarda o resultado de proposito, e nada a remove.
SOB_DEMANDA_COM_AMEACA = _job(
    "clamav-tray-scan.service", user=True, status=1, active="failed", sub="failed",
    finished=datetime(2026, 9, 25, 19, 17, 19, tzinfo=TZ),
)

# A agendada rodou limpa nos tres dias seguintes. Esta e a de 28/09.
AGENDADA_LIMPA = _job(
    "clamav-scan.service", user=False, status=0,
    finished=datetime(2026, 9, 28, 7, 46, 39, tzinfo=TZ),
)


def test_varredura_recente_vence_a_antiga_mesmo_sendo_de_outro_barramento():
    """O bug: o escopo decidia, a data nao era consultada.

    Antes, `pick_scan_unit` ordenava por `not user_scope` e a sob demanda ganhava
    sempre. Como a escolha da unidade acontece ANTES da leitura do resumo, as
    varreduras limpas de 26, 27 e 28 nunca chegavam a ser lidas.
    """
    estado = {u.id: u for u in (SOB_DEMANDA_COM_AMEACA, AGENDADA_LIMPA)}
    assert pick_scan_unit(estado) is AGENDADA_LIMPA


def test_sob_demanda_vence_enquanto_e_a_mais_recente():
    """A preferencia antiga nao era gratuita: logo apos o clique ela esta certa.

    O que mudou e o motivo — agora ela ganha por ser recente, nao por ser do
    usuario."""
    recem_terminada = _job(
        "clamav-tray-scan.service", user=True, status=0,
        finished=datetime(2026, 9, 28, 9, 0, 0, tzinfo=TZ),
    )
    estado = {u.id: u for u in (recem_terminada, AGENDADA_LIMPA)}
    assert pick_scan_unit(estado) is recem_terminada


def test_rodando_agora_vence_qualquer_resultado_terminado():
    """Progresso e mais urgente que veredito: o que esta acontecendo agora tem de
    aparecer, mesmo que o ultimo resultado seja mais novo no relogio."""
    rodando = _job(
        "clamav-tray-scan.service", user=True, active="active", sub="running",
        status=None, finished=None,
    )
    estado = {u.id: u for u in (rodando, AGENDADA_LIMPA)}
    escolhida = pick_scan_unit(estado)
    assert escolhida is rodando
    assert escolhida.is_running_job


def test_unidade_que_nunca_rodou_fica_por_ultimo():
    """Sem `finished_at` nao ha o que relatar; nao pode passar na frente de quem
    tem resultado."""
    nunca = _job("clamav-tray-scan.service", user=True, status=None, finished=None)
    estado = {u.id: u for u in (nunca, AGENDADA_LIMPA)}
    assert pick_scan_unit(estado) is AGENDADA_LIMPA


def test_sem_tarefa_nenhuma_devolve_none():
    daemon = Unit(
        id="clamav-daemon.service", kind=Kind.DAEMON, active_state="active",
        sub_state="running", result="success",
    )
    assert pick_scan_unit({daemon.id: daemon}) is None
    assert pick_full_scan_unit({daemon.id: daemon}) is None


def test_varredura_completa_continua_preferindo_o_sistema():
    """`pick_full_scan_unit` NAO muda com esta correcao.

    Ela responde outra pergunta — "esta maquina esta protegida?" — e uma varredura
    de 4 segundos num pendrive nao responde isso, por mais recente que seja.
    """
    estado = {u.id: u for u in (SOB_DEMANDA_COM_AMEACA, AGENDADA_LIMPA)}
    assert pick_full_scan_unit(estado) is AGENDADA_LIMPA
