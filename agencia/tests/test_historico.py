import httpx
from fastapi.testclient import TestClient

from agencia.app.auth import token_agencia
from agencia.app.main import criar_aplicacao


def cliente(tmp_path, agencia=0, transporte=None):
    c = TestClient(criar_aplicacao(agencia, tmp_path, transporte_http=transporte))
    token = c.post("/auth/login", json={"usuario": "aluno", "senha": "senha-teste"}).json()["access_token"]
    c.headers["Authorization"] = "Bearer " + token
    return c


def criar(c, id):
    assert c.post("/contas", json={"id": id, "nomeAluno": "Aluno", "saldoInicial": "100.00"}).status_code == 201


def test_historico_isola_contas_e_ordena_operacoes(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        criar(c, 3)
        c.post("/contas/0/depositar", json={"valor": "10.00"})
        c.post("/contas/0/sacar", json={"valor": "5.00"})
        c.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": "20.00"})
        h = c.get("/contas/0/historico").json()
        assert h["saldoAtual"] == "85.00"
        assert [e["tipo"] for e in h["eventos"]] == ["CRIAR_CONTA", "DEPOSITO", "SAQUE", "TRANSFERENCIA_DEBITO"]
        assert [e["timestampLamport"] for e in h["eventos"]] == [1, 3, 4, 5]
        h = c.get("/contas/3/historico").json()
        assert h["saldoAtual"] == "120.00"
        assert [e["tipo"] for e in h["eventos"]] == ["CRIAR_CONTA", "TRANSFERENCIA_CREDITO"]
        pag = c.get("/contas/0/historico?offset=1&limite=2").json()
        assert pag["total"] == 4
        assert [e["tipo"] for e in pag["eventos"]] == ["DEPOSITO", "SAQUE"]
        assert c.get("/contas/0/historico?offset=99").json()["eventos"] == []
        for query in ("limite=0", "limite=101", "offset=-1"):
            assert c.get("/contas/0/historico?"+query).status_code == 422
        assert c.get("/contas/999/historico").status_code == 404
        assert c.get("/contas/0/historico", headers={"Authorization": ""}).status_code == 401


def test_historico_falha_remota_nao_simula_compensacao(tmp_path):
    with cliente(tmp_path, transporte=httpx.MockTransport(lambda r: httpx.Response(503))) as c:
        criar(c, 0)
        assert c.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": "5.00"}).status_code == 502
        h = c.get("/contas/0/historico").json()
        assert h["saldoAtual"] == "95.00"
        assert [e["tipo"] for e in h["eventos"]] == ["CRIAR_CONTA", "TRANSFERENCIA_DEBITO", "TRANSFERENCIA_FALHOU"]
        assert h["eventos"][-1]["detalhes"]["debitoAplicado"] is True


def test_historico_credito_remoto_e_reinicio(tmp_path):
    with cliente(tmp_path, agencia=1) as c:
        criar(c, 1)
        corpo = {"valor": "2.50", "timestampLamport": 4, "origemAgencia": 0}
        rota = "/contas/1/creditar-remoto"
        token = token_agencia(c.app.state.auth, 0, 1, rota, corpo)
        assert c.post(rota, json=corpo, headers={"Authorization": "Bearer " + token}).status_code == 200
        h = c.get("/contas/1/historico").json()
        assert h["eventos"][-1]["tipo"] == "TRANSFERENCIA_CREDITO_REMOTO"
        assert h["eventos"][-1]["timestampLamport"] == 5
        assert h["saldoAtual"] == "102.50"
    with cliente(tmp_path, agencia=1) as novo:
        assert novo.get("/contas/1/historico").status_code == 404
        criar(novo, 1)
        assert novo.get("/contas/1/historico").json()["total"] == 1


def test_saque_rejeitado_nao_cria_evento(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        assert c.post("/contas/0/sacar", json={"valor": "101.00"}).status_code == 400
        assert c.get("/contas/0/historico").json()["total"] == 1


def test_destino_local_ausente_historico_reconcilia_saldo(tmp_path):
    with cliente(tmp_path) as c:
        criar(c, 0)
        assert c.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": "10.00"}).status_code == 404
        h = c.get("/contas/0/historico").json()
        assert h["saldoAtual"] == "100.00"
        assert [e["tipo"] for e in h["eventos"]] == ["CRIAR_CONTA", "TRANSFERENCIA_DEBITO", "ESTORNO_LOCAL"]
        assert h["eventos"][-1]["detalhes"]["saldo"] == h["saldoAtual"]
        assert [e["timestampLamport"] for e in h["eventos"]] == [1, 2, 3]
