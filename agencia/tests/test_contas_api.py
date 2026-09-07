"""Testes da API REST de contas."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agencia.app.main import criar_aplicacao


@pytest.fixture
def cliente(tmp_path: Path) -> TestClient:
    with TestClient(criar_aplicacao(0, tmp_path)) as cliente_teste:
        token = cliente_teste.post("/auth/login", json={"usuario": "aluno", "senha": "senha-teste"}).json()["access_token"]
        cliente_teste.headers["Authorization"] = f"Bearer {token}"
        yield cliente_teste


def criar_conta(cliente: TestClient, conta_id: int = 0, saldo: str = "100.00") -> None:
    resposta = cliente.post(
        "/contas",
        json={"id": conta_id, "nomeAluno": "Ana", "saldoInicial": saldo},
    )
    assert resposta.status_code == 201


def test_cria_e_consulta_conta_com_saldo_monetario_consistente(
    cliente: TestClient,
    tmp_path: Path,
) -> None:
    resposta_criacao = cliente.post(
        "/contas",
        json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100},
    )

    assert resposta_criacao.status_code == 201
    assert resposta_criacao.json() == {
        "id": 0,
        "nomeAluno": "Ana",
        "saldo": "100.00",
    }
    assert cliente.get("/contas/0").json() == resposta_criacao.json()

    evento = json.loads((tmp_path / "eventos-agencia-0.jsonl").read_text(encoding="utf-8"))
    assert evento["tipo"] == "CRIAR_CONTA"
    assert evento["timestampLamport"] == 1
    assert evento["detalhes"]["saldo"] == "100.00"


def test_rejeita_conta_de_outra_agencia(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/contas",
        json={"id": 1, "nomeAluno": "Bia", "saldoInicial": "20.00"},
    )

    assert resposta.status_code == 400
    assert "pertence à Agência 1" in resposta.json()["detail"]


def test_rejeita_conta_duplicada(cliente: TestClient) -> None:
    criar_conta(cliente)

    resposta = cliente.post(
        "/contas",
        json={"id": 0, "nomeAluno": "Outra", "saldoInicial": "1.00"},
    )

    assert resposta.status_code == 409


@pytest.mark.parametrize(
    "corpo",
    [
        {"id": -1, "nomeAluno": "Ana", "saldoInicial": "10.00"},
        {"id": 0, "nomeAluno": "", "saldoInicial": "10.00"},
        {"id": 0, "nomeAluno": "   ", "saldoInicial": "10.00"},
        {"id": 0, "nomeAluno": "Ana", "saldoInicial": "-0.01"},
        {"id": 0, "nomeAluno": "Ana", "saldoInicial": "1.001"},
        {"id": 0, "nomeAluno": "Ana"},
    ],
)
def test_rejeita_dados_invalidos_na_criacao(cliente: TestClient, corpo: dict[str, object]) -> None:
    resposta = cliente.post("/contas", json=corpo)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Dados da requisição inválidos."


def test_rejeita_corpo_malformado(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/contas",
        content="{json quebrado",
        headers={"content-type": "application/json"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["erros"][0]["mensagem"] == "O corpo não contém um JSON válido."


def test_deposita_e_saca_com_novos_eventos(cliente: TestClient, tmp_path: Path) -> None:
    criar_conta(cliente)

    deposito = cliente.post("/contas/0/depositar", json={"valor": "25.00"})
    saque = cliente.post("/contas/0/sacar", json={"valor": "20.50"})

    assert deposito.status_code == 200
    assert deposito.json()["saldo"] == "125.00"
    assert saque.status_code == 200
    assert saque.json()["saldo"] == "104.50"
    eventos = [
        json.loads(linha)
        for linha in (tmp_path / "eventos-agencia-0.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [evento["tipo"] for evento in eventos] == ["CRIAR_CONTA", "DEPOSITO", "SAQUE"]
    assert [evento["timestampLamport"] for evento in eventos] == [1, 2, 3]
    assert eventos[-1]["detalhes"]["saldo"] == "104.50"


@pytest.mark.parametrize("rota", ["depositar", "sacar"])
@pytest.mark.parametrize("valor", [0, -1])
def test_rejeita_operacao_com_valor_nao_positivo(
    cliente: TestClient,
    rota: str,
    valor: int,
) -> None:
    criar_conta(cliente)

    resposta = cliente.post(f"/contas/0/{rota}", json={"valor": valor})

    assert resposta.status_code == 422


@pytest.mark.parametrize("rota", ["depositar", "sacar"])
def test_operacao_em_conta_inexistente_retorna_404(
    cliente: TestClient,
    rota: str,
) -> None:
    resposta = cliente.post(f"/contas/99/{rota}", json={"valor": "1.00"})

    assert resposta.status_code == 404


def test_rejeita_saque_com_saldo_insuficiente_sem_alterar_saldo(cliente: TestClient) -> None:
    criar_conta(cliente, saldo="10.00")

    resposta = cliente.post("/contas/0/sacar", json={"valor": "10.01"})

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Saldo insuficiente para realizar o saque."
    assert cliente.get("/contas/0").json()["saldo"] == "10.00"


def test_consulta_conta_inexistente_retorna_404(cliente: TestClient) -> None:
    assert cliente.get("/contas/300").status_code == 404


@pytest.mark.parametrize(
    "caminho",
    ["/contas/-1", "/contas/-1/depositar", "/contas/-1/sacar"],
)
def test_rejeita_identificador_negativo_na_rota(cliente: TestClient, caminho: str) -> None:
    if caminho == "/contas/-1":
        resposta = cliente.get(caminho)
    else:
        resposta = cliente.post(caminho, json={"valor": "1.00"})

    assert resposta.status_code == 422
