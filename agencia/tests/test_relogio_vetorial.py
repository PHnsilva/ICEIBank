from concurrent.futures import ThreadPoolExecutor

import pytest

from agencia.app.services.relogio_vetorial import RelogioVetorial, comparar_vetores


def test_regras_e_snapshots_independentes():
    origem, destino = RelogioVetorial(0), RelogioVetorial(1)
    assert origem.evento_local() == [1, 0, 0]
    enviado = origem.ao_enviar()
    assert enviado == [2, 0, 0]
    assert destino.evento_local() == [0, 1, 0]
    assert destino.ao_receber(enviado) == [2, 2, 0]
    enviado[0] = 999
    snapshot = destino.valor
    snapshot[1] = 999
    assert origem.valor == [2, 0, 0]
    assert destino.valor == [2, 2, 0]
    assert destino.ao_receber([1, 0, 5]) == [2, 3, 5]


@pytest.mark.parametrize("primeiro,segundo,esperado", [
    ([3, 1, 0], [3, 2, 0], "ANTES"),
    ([3, 2, 0], [3, 1, 0], "DEPOIS"),
    ([3, 1, 0], [1, 3, 0], "CONCORRENTES"),
    ([0, 0, 0], [0, 0, 0], "IGUAIS"),
])
def test_relacoes_do_roteiro(primeiro, segundo, esperado):
    assert comparar_vetores(primeiro, segundo) == esperado


@pytest.mark.parametrize("vetor", [[1, 2], [1, 2, 3, 4], [1, -1, 0], [True, 0, 0], [1.5, 0, 0], None])
def test_mensagem_invalida_nao_altera_relogio(vetor):
    relogio = RelogioVetorial(0)
    with pytest.raises(ValueError):
        relogio.ao_receber(vetor)
    assert relogio.valor == [0, 0, 0]


def test_incrementos_concorrentes_nao_se_perdem():
    relogio = RelogioVetorial(2)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: relogio.evento_local(), range(1000)))
    assert relogio.valor == [0, 0, 1000]


def test_crescimento_para_dez_agencias():
    assert RelogioVetorial(9, 10).evento_local() == [0] * 9 + [1]
