"""Testes da configuração e do particionamento de contas."""

import pytest

from agencia.app.config import (
    NUMERO_AGENCIAS,
    OFFSET,
    PORTA_BASE,
    PORTAS_AGENCIAS,
    URLS_AGENCIAS,
    agencia_responsavel,
    porta_da_agencia,
    url_da_agencia,
    validar_agencia_id,
)


def test_offset_numero_de_agencias_e_porta_base() -> None:
    assert OFFSET == 78
    assert NUMERO_AGENCIAS == 3
    assert PORTA_BASE == 4078


def test_portas_e_urls_das_agencias() -> None:
    assert PORTAS_AGENCIAS == (4078, 4079, 4080)
    assert URLS_AGENCIAS == (
        "http://localhost:4078",
        "http://localhost:4079",
        "http://localhost:4080",
    )
    assert porta_da_agencia(2) == 4080
    assert url_da_agencia(1) == "http://localhost:4079"


@pytest.mark.parametrize(
    ("id_conta", "agencia_esperada"),
    [(0, 0), (1, 1), (2, 2), (3, 0), (10, 1)],
)
def test_particionamento_de_contas(id_conta: int, agencia_esperada: int) -> None:
    assert agencia_responsavel(id_conta) == agencia_esperada


@pytest.mark.parametrize("agencia_id", [-1, 3, 100])
def test_rejeita_identificador_de_agencia_invalido(agencia_id: int) -> None:
    with pytest.raises(ValueError, match="AGENCIA_ID deve estar entre 0 e 2"):
        validar_agencia_id(agencia_id)
