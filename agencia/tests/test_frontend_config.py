from fastapi.testclient import TestClient
from agencia.app.main import criar_aplicacao


def test_frontend_publico_e_cors_restrito(tmp_path):
    with TestClient(criar_aplicacao(1, tmp_path)) as c:
        pagina = c.get("/")
        assert pagina.status_code == 200
        assert "ICEIBank" in pagina.text
        assert "frame-ancestors 'none'" in pagina.headers["content-security-policy"]
        assert c.get("/static/app.js").status_code == 200
        assert c.get("/config").json()["agenciaAtual"] == 1
        r = c.options("/contas", headers={"Origin": "http://localhost:4078", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:4078"
        r = c.options("/contas", headers={"Origin": "https://estranho.example", "Access-Control-Request-Method": "POST"})
        assert r.status_code == 400
        assert "access-control-allow-origin" not in r.headers
