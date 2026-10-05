import json

import pytest
from fastapi.testclient import TestClient

from agencia.app.main import criar_aplicacao
from agencia.app.services.creditos import processar_credito


def cliente(tmp_path, agencia=0):
    c = TestClient(criar_aplicacao(agencia, tmp_path))
    token = c.post("/auth/login", json={"usuario": "aluno", "senha": "senha-teste"}).json()["access_token"]
    c.headers["Authorization"] = "Bearer " + token
    return c


def criar(c, id, saldo="100.00"):
    assert c.post("/contas", json={"id": id, "nomeAluno": "Aluno", "saldoInicial": saldo}).status_code == 201


def test_local_credita_e_nao_publica(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        criar(c, 3, "50.00")
        r = c.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": "10.00"})
        assert r.status_code == 200
        assert r.json()["status"] == "concluida"
        assert r.json()["saldoDestino"] == "60.00"
        assert c.get("/contas/0").json()["saldo"] == "90.00"
        assert c.app.state.estado_agencia.relogio.valor == [4, 0, 0]
        assert not c.app.state.mensageria.publicadas


def test_publicacao_nao_afirma_credito_e_propaga_vetor(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        r = c.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": "30.00"})
        assert r.status_code == 200
        assert r.json()["status"] == "publicada"
        assert "saldoDestino" not in r.json()
        assert r.json()["saldoOrigem"] == "70.00"
        key, corpo = c.app.state.mensageria.publicadas[0]
        assert key == "agencia.1.creditar"
        assert corpo == {"idConta": 1, "idOrigem": 0, "valor": "30.00", "vetorEnvio": [3, 0, 0],
                         "origemAgencia": 0, "idTransferencia": r.json()["idTransferencia"]}
        eventos = [json.loads(l) for l in (tmp_path / "eventos-agencia-0.jsonl").read_text().splitlines()]
        assert eventos[-1]["tipo"] == "TRANSFERENCIA_PUBLICADA"
        assert eventos[-1]["timestampVetorial"] == [3, 0, 0]


def test_falha_publicacao_mantem_limitacao_e_registra_incerteza(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        c.app.state.mensageria.falhar = True
        r = c.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": "5.00"})
        assert r.status_code == 502
        assert "não foi restaurado" in r.json()["detail"]
        assert c.get("/contas/0").json()["saldo"] == "95.00"
        assert c.get("/contas/0/historico").json()["eventos"][-1]["tipo"] == "TRANSFERENCIA_FALHOU"


def test_consumidor_combina_vetor_e_credita(tmp_path):
    with cliente(tmp_path, 1) as c:
        criar(c, 1)
        assert c.portal.call(processar_credito, c.app.state.estado_agencia,
            {"idConta": 1, "valor": "30.00", "origemAgencia": 0, "vetorEnvio": [3, 0, 0]})
        assert c.get("/contas/1").json()["saldo"] == "130.00"
        assert c.app.state.estado_agencia.relogio.valor == [3, 2, 0]


def test_conta_ausente_rejeita_mas_registra_recebimento(tmp_path):
    with cliente(tmp_path, 1) as c:
        assert c.portal.call(processar_credito, c.app.state.estado_agencia,
            {"idConta": 1, "valor": "30.00", "origemAgencia": 0, "vetorEnvio": [3, 0, 0]}) is False
        assert c.app.state.estado_agencia.relogio.valor == [3, 1, 0]
        assert "CREDITO_REMOTO_FALHOU" in (tmp_path / "eventos-agencia-1.jsonl").read_text()


@pytest.mark.parametrize("alteracoes", [
    {"vetorEnvio": [1, 2]}, {"vetorEnvio": [True, 0, 0]}, {"valor": "-1.00"},
    {"valor": "1.001"}, {"idConta": 0}, {"origemAgencia": 1}, {"idOrigem": 2},
])
def test_mensagem_invalida_nao_credita(tmp_path, alteracoes):
    with cliente(tmp_path, 1) as c:
        criar(c, 1)
        corpo = {"idConta": 1, "valor": "30.00", "origemAgencia": 0, "vetorEnvio": [3, 0, 0]}
        assert c.portal.call(processar_credito, c.app.state.estado_agencia, {**corpo, **alteracoes}) is False
        assert c.get("/contas/1").json()["saldo"] == "100.00"
        assert c.app.state.estado_agencia.relogio.valor == [0, 2, 0]


def test_rejeicoes_nao_publicam_ou_alteram_saldo(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0, "5.00")
        for origem, valor, status in [(3, "1.00", 404), (0, "6.00", 400), (0, "0.00", 422)]:
            assert c.post("/transferencias", json={"idOrigem": origem, "idDestino": 1, "valor": valor}).status_code == status
        assert c.get("/contas/0").json()["saldo"] == "5.00"
        assert not c.app.state.mensageria.publicadas
