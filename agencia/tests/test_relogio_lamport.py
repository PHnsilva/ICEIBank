"""Testes do relógio lógico de Lamport."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from agencia.app.services.relogio_lamport import RelogioLamport


def test_evento_local_incrementa_e_retorna_contador() -> None:
    relogio = RelogioLamport()

    assert relogio.evento_local() == 1
    assert relogio.evento_local() == 2
    assert relogio.valor == 2


def test_ao_enviar_incrementa_e_retorna_contador() -> None:
    relogio = RelogioLamport(valor_inicial=4)

    assert relogio.ao_enviar() == 5
    assert relogio.valor == 5


@pytest.mark.parametrize(
    ("valor_local", "timestamp_recebido", "resultado"),
    [(2, 7, 8), (10, 3, 11), (5, 5, 6)],
)
def test_ao_receber_combina_os_relogios(
    valor_local: int,
    timestamp_recebido: int,
    resultado: int,
) -> None:
    relogio = RelogioLamport(valor_inicial=valor_local)

    assert relogio.ao_receber(timestamp_recebido) == resultado
    assert relogio.valor == resultado


def test_incrementos_concorrentes_nao_sao_perdidos() -> None:
    relogio = RelogioLamport()

    with ThreadPoolExecutor(max_workers=8) as executor:
        resultados = list(executor.map(lambda _: relogio.evento_local(), range(500)))

    assert relogio.valor == 500
    assert sorted(resultados) == list(range(1, 501))


def test_rejeita_valores_negativos() -> None:
    with pytest.raises(ValueError):
        RelogioLamport(-1)

    with pytest.raises(ValueError):
        RelogioLamport().ao_receber(-1)
