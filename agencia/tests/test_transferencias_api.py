"""Testes das transferências locais e entre agências."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from agencia.app.main import criar_aplicacao
from agencia.app.auth import token_agencia


def _cliente(
    agencia_id: int,
    diretorio: Path,
    transporte: httpx.AsyncBaseTransport | None = None,
) -> TestClient:
    cliente = TestClient(criar_aplicacao(agencia_id, diretorio, transporte_http=transporte))
    token = cliente.post("/auth/login", json={"usuario": "aluno", "senha": "senha-teste"}).json()["access_token"]
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _criar_conta(
    cliente: TestClient,
    conta_id: int,
    saldo: str,
    nome: str = "Aluno",
) -> None:
    resposta = cliente.post(
        "/contas",
        json={"id": conta_id, "nomeAluno": nome, "saldoInicial": saldo},
    )
    assert resposta.status_code == 201


def _eventos(caminho: Path) -> list[dict[str, object]]:
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]


def test_transferencia_local_credita_destino_sem_salto_de_envio(tmp_path: Path) -> None:
    with _cliente(0, tmp_path) as cliente:
        _criar_conta(cliente, 0, "100.00", "Ana")
        _criar_conta(cliente, 3, "50.00", "Caio")

        resposta = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 3, "valor": "10.00"},
        )

        assert resposta.status_code == 200
        assert resposta.json() == {
            "mensagem": "Transferência local realizada com sucesso.",
            "tipo": "local",
            "idOrigem": 0,
            "idDestino": 3,
            "valor": "10.00",
            "saldoOrigem": "90.00",
            "saldoDestino": "60.00",
        }
        assert cliente.get("/contas/0").json()["saldo"] == "90.00"
        assert cliente.get("/contas/3").json()["saldo"] == "60.00"
        assert cliente.app.state.estado_agencia.relogio.valor == 4

    eventos = _eventos(tmp_path / "eventos-agencia-0.jsonl")
    assert [evento["tipo"] for evento in eventos] == [
        "CRIAR_CONTA",
        "CRIAR_CONTA",
        "TRANSFERENCIA_DEBITO",
        "TRANSFERENCIA_CREDITO",
    ]
    assert [evento["timestampLamport"] for evento in eventos] == [1, 2, 3, 4]


def test_destino_local_inexistente_restaura_debito(tmp_path: Path) -> None:
    with _cliente(0, tmp_path) as cliente:
        _criar_conta(cliente, 0, "100.00")

        resposta = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 3, "valor": "10.00"},
        )

        assert resposta.status_code == 404
        assert "débito local foi restaurado" in resposta.json()["detail"]
        assert cliente.get("/contas/0").json()["saldo"] == "100.00"


def test_transferencia_entre_agencias_envia_timestamp_e_confirma_credito(
    tmp_path: Path,
) -> None:
    requisicao_recebida: dict[str, object] = {}

    def responder(requisicao: httpx.Request) -> httpx.Response:
        requisicao_recebida.update(json.loads(requisicao.content))
        assert str(requisicao.url) == "http://localhost:4079/contas/1/creditar-remoto"
        return httpx.Response(200, json={"id": 1, "saldo": "80.00", "timestampLamport": 4})

    transporte = httpx.MockTransport(responder)
    with _cliente(0, tmp_path, transporte) as cliente:
        _criar_conta(cliente, 0, "100.00")

        resposta = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 1, "valor": "30.00"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["tipo"] == "entre-agencias"
        assert resposta.json()["saldoOrigem"] == "70.00"
        assert resposta.json()["saldoDestino"] == "80.00"
        assert requisicao_recebida == {
            "valor": "30.00",
            "timestampLamport": 3,
            "origemAgencia": 0,
        }
        assert cliente.app.state.estado_agencia.relogio.valor == 3


@pytest.mark.parametrize("modo", ["indisponivel", "rejeitada", "resposta-invalida"])
def test_falha_remota_mantem_debito_retorna_502_e_registra_evento(
    tmp_path: Path,
    modo: str,
) -> None:
    def falhar(requisicao: httpx.Request) -> httpx.Response:
        if modo == "indisponivel":
            raise httpx.ConnectError("destino indisponível", request=requisicao)
        if modo == "resposta-invalida":
            return httpx.Response(200, text="resposta sem JSON")
        return httpx.Response(404, json={"detail": "Conta ausente."})

    with _cliente(0, tmp_path, httpx.MockTransport(falhar)) as cliente:
        _criar_conta(cliente, 0, "100.00")

        resposta = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 1, "valor": "5.00"},
        )

        assert resposta.status_code == 502
        assert "débito de R$ 5.00 já foi aplicado" in resposta.json()["detail"]
        assert "Sprint 4" in resposta.json()["detail"]
        assert cliente.get("/contas/0").json()["saldo"] == "95.00"

    eventos = _eventos(tmp_path / "eventos-agencia-0.jsonl")
    assert [evento["tipo"] for evento in eventos] == [
        "CRIAR_CONTA",
        "TRANSFERENCIA_DEBITO",
        "TRANSFERENCIA_FALHOU",
    ]
    assert [evento["timestampLamport"] for evento in eventos] == [1, 2, 4]
    assert eventos[-1]["detalhes"]["debitoAplicado"] is True  # type: ignore[index]


def test_credito_remoto_atualiza_relogio_antes_de_creditar(tmp_path: Path) -> None:
    with _cliente(1, tmp_path) as cliente:
        _criar_conta(cliente, 1, "50.00", "Bia")

        resposta = cliente.post(
            "/contas/1/creditar-remoto",
            json={"valor": "30.00", "timestampLamport": 3, "origemAgencia": 0},
            headers={"Authorization": "Bearer " + token_agencia(cliente.app.state.auth, 0, 1,
                     "/contas/1/creditar-remoto", {"valor": "30.00", "timestampLamport": 3, "origemAgencia": 0})},
        )

        assert resposta.status_code == 200
        assert resposta.json() == {"id": 1, "saldo": "80.00", "timestampLamport": 4}

    eventos = _eventos(tmp_path / "eventos-agencia-1.jsonl")
    assert eventos[-1]["tipo"] == "TRANSFERENCIA_CREDITO_REMOTO"
    assert eventos[-1]["timestampLamport"] == 4
    assert eventos[-1]["detalhes"]["origemAgencia"] == 0  # type: ignore[index]


def test_credito_remoto_em_conta_inexistente_ainda_atualiza_relogio(tmp_path: Path) -> None:
    with _cliente(1, tmp_path) as cliente:
        resposta = cliente.post(
            "/contas/1/creditar-remoto",
            json={"valor": "1.00", "timestampLamport": 10, "origemAgencia": 0},
            headers={"Authorization": "Bearer " + token_agencia(cliente.app.state.auth, 0, 1,
                     "/contas/1/creditar-remoto", {"valor": "1.00", "timestampLamport": 10, "origemAgencia": 0})},
        )

        assert resposta.status_code == 404
        assert cliente.app.state.estado_agencia.relogio.valor == 11


def test_rejeita_transferencia_sem_origem_local_e_saldo_insuficiente(tmp_path: Path) -> None:
    with _cliente(0, tmp_path) as cliente:
        sem_origem = cliente.post(
            "/transferencias",
            json={"idOrigem": 1, "idDestino": 0, "valor": "1.00"},
        )
        assert sem_origem.status_code == 404

        _criar_conta(cliente, 0, "10.00")
        sem_saldo = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 1, "valor": "10.01"},
        )
        assert sem_saldo.status_code == 400
        assert cliente.get("/contas/0").json()["saldo"] == "10.00"


@pytest.mark.parametrize("valor", [0, -1])
def test_rejeita_transferencia_com_valor_nao_positivo(tmp_path: Path, valor: int) -> None:
    with _cliente(0, tmp_path) as cliente:
        resposta = cliente.post(
            "/transferencias",
            json={"idOrigem": 0, "idDestino": 1, "valor": valor},
        )

        assert resposta.status_code == 422
