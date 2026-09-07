import jwt
import pytest
from fastapi.testclient import TestClient

from agencia.app.auth import ConfiguracaoAuth, emitir_token, token_agencia
from agencia.app.main import criar_aplicacao


@pytest.fixture
def cliente(tmp_path):
    with TestClient(criar_aplicacao(0, tmp_path)) as c:
        yield c


def entrar(c):
    return c.post("/auth/login", json={"usuario": "aluno", "senha": "senha-teste"})


@pytest.mark.parametrize("metodo,rota,corpo", [
    ("GET", "/contas/0", None), ("POST", "/contas", {}),
    ("GET", "/contas/0/historico", None),
    ("POST", "/contas/0/depositar", {"valor": 1}),
    ("POST", "/contas/0/sacar", {"valor": 1}),
    ("POST", "/transferencias", {}),
    ("POST", "/contas/0/creditar-remoto", {}),
])
def test_todas_rotas_exigem_token(cliente, metodo, rota, corpo):
    r = cliente.request(metodo, rota, json=corpo)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"
    assert not cliente.app.state.estado_agencia.contas
    assert cliente.app.state.estado_agencia.relogio.valor == 0


def test_login_e_token_valido(cliente):
    r = entrar(cliente)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["expires_in"] == 900
    cliente.headers["Authorization"] = "Bearer " + r.json()["access_token"]
    assert cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 10}).status_code == 201
    assert cliente.get("/contas/0").json()["saldo"] == "10.00"


@pytest.mark.parametrize("usuario,senha", [("aluno", "errada"), ("outro", "senha-teste")])
def test_login_invalido(cliente, usuario, senha):
    r = cliente.post("/auth/login", json={"usuario": usuario, "senha": senha})
    assert r.status_code == 401
    assert "access_token" not in r.json()


@pytest.mark.parametrize("caso", ["expirado", "assinatura", "audiencia", "emissor", "sem-exp", "alg-none", "malformado", "tipo", "futuro"])
def test_rejeita_tokens_invalidos(cliente, caso):
    key = cliente.app.state.auth.segredo_usuario
    token = emitir_token(key, "aluno", "iceibank-api", -1 if caso == "expirado" else 900, tipo="usuario")
    claims = jwt.decode(token, options={"verify_signature": False})
    if caso == "assinatura": key = "outra-chave-" * 4
    if caso == "audiencia": claims["aud"] = "outra-api"
    if caso == "emissor": claims["iss"] = "outro"
    if caso == "sem-exp": del claims["exp"]
    if caso == "tipo": claims["tipo"] = "agencia"
    if caso == "futuro": claims["nbf"] += 3600
    token = jwt.encode(claims, key, algorithm="HS256")
    if caso == "alg-none": token = jwt.encode(claims, "", algorithm="none")
    if caso == "malformado": token = "nao.e.jwt"
    r = cliente.get("/contas/0", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 401
    if caso == "expirado": assert "expirado" in r.json()["detail"]


def test_usuario_nao_pode_creditar_remoto(cliente):
    cliente.headers["Authorization"] = "Bearer " + entrar(cliente).json()["access_token"]
    r = cliente.post("/contas/0/creditar-remoto", json={"valor": "1.00", "timestampLamport": 1, "origemAgencia": 1})
    assert r.status_code == 401
    assert cliente.app.state.estado_agencia.relogio.valor == 0


@pytest.mark.parametrize("caso", ["valido", "valor-alterado", "origem-alterada", "destino-errado", "rota-alterada", "usuario"])
def test_autenticacao_entre_agencias(cliente, caso):
    corpo = {"valor": "1.00", "timestampLamport": 1, "origemAgencia": 1}
    rota = "/contas/0/creditar-remoto"
    token = token_agencia(cliente.app.state.auth, 1, 2 if caso == "destino-errado" else 0, rota, corpo)
    if caso == "valor-alterado": corpo["valor"] = "100.00"
    if caso == "origem-alterada": corpo["origemAgencia"] = 2
    if caso == "rota-alterada": rota = "/contas/3/creditar-remoto"
    if caso == "usuario": rota = "/contas/0"
    if caso == "usuario": r = cliente.get(rota, headers={"Authorization": "Bearer " + token})
    else: r = cliente.post(rota, json=corpo, headers={"Authorization": "Bearer " + token})
    assert r.status_code == (404 if caso == "valido" else 401)
    assert cliente.app.state.estado_agencia.relogio.valor == (2 if caso == "valido" else 0)


def test_configuracao_sem_segredos_falha(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(ValueError, match="Configure"):
        ConfiguracaoAuth.do_ambiente()


def test_mensagem_agencia_corpo_nao_objeto_retorna_401(cliente):
    token = emitir_token(cliente.app.state.auth.segredo_agencias, "agencia-1", "agencia-0", 30, tipo="agencia")
    r = cliente.post("/contas/0/creditar-remoto", json=[], headers={"Authorization": "Bearer " + token})
    assert r.status_code == 401
    assert cliente.app.state.estado_agencia.relogio.valor == 0
