from agencia.app.auth import ConfiguracaoAuth
from agencia.app.services.eleicao import Eleicao, PRAZO_MAIORIA


def test_preserva_voto_apos_reinicio_e_rejeita_mandato_anterior(tmp_path, monkeypatch):
    agora = 10.0
    monkeypatch.setattr("agencia.app.services.eleicao.monotonic", lambda: agora)
    arquivo = tmp_path / "voto.json"
    auth = ConfiguracaoAuth.do_ambiente()
    eleicao = Eleicao(0, arquivo, auth)
    assert eleicao.votar(1, 1)["aceito"]
    eleicao = Eleicao(0, arquivo, auth)
    assert not eleicao.votar(2, 1)["aceito"]
    assert not eleicao.votar(2, 2)["aceito"]
    agora += PRAZO_MAIORIA + 0.1
    assert eleicao.votar(2, 2)["aceito"]
    assert not eleicao.receber_batimento(1, 1)["aceito"]


def test_batimento_mantem_protecao_ate_expirar(tmp_path, monkeypatch):
    agora = 10.0
    monkeypatch.setattr("agencia.app.services.eleicao.monotonic", lambda: agora)
    eleicao = Eleicao(0, tmp_path / "voto.json", ConfiguracaoAuth.do_ambiente())
    assert eleicao.receber_batimento(1, 1)["aceito"]
    assert eleicao.status()["liderId"] == 1
    assert not eleicao.votar(2, 2)["aceito"]
    agora += 2.1
    assert eleicao.status()["liderId"] is None
    assert eleicao.votar(2, 2)["aceito"]
