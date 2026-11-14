import pytest

from agencia.app.auth import ConfiguracaoAuth, token_agencia
from agencia.app.main import criar_aplicacao
from agencia.app.services.eleicao import _segundos_configurados
from fastapi.testclient import TestClient


def test_bully_respeita_prioridade_e_rejeita_mensagem_sem_jwt(tmp_path):
    app = criar_aplicacao(1, tmp_path, ativar_eleicao=True)
    with TestClient(app) as cliente:
        voto = {"origemId": 0, "vetorEnvio": [1, 0, 0]}
        caminho = "/bully/eleicao"
        assert cliente.post(caminho, json=voto).status_code == 401
        resposta = cliente.post(caminho, json=voto, headers={
            "Authorization": "Bearer " + token_agencia(ConfiguracaoAuth.do_ambiente(), 0, 1, caminho, voto),
        })
        assert resposta.status_code == 200


@pytest.mark.parametrize(("id_local", "lider_recebida", "esperada"), [(1, 0, None), (0, 2, 2)])
def test_anuncio_de_coordenador_prioriza_id_maior(tmp_path, id_local, lider_recebida, esperada):
    app = criar_aplicacao(id_local, tmp_path, ativar_eleicao=True)
    eleicao = app.state.eleicao
    eleicao.receber_coordenador(lider_recebida, [0, 1, 2])
    assert eleicao.status() == {"idAgencia": id_local, "liderAtual": esperada}


def test_tempos_do_bully_podem_ser_configurados(tmp_path, monkeypatch):
    monkeypatch.setenv("BULLY_HEARTBEAT_SEGUNDOS", "1.5")
    monkeypatch.setenv("BULLY_TIMEOUT_SEGUNDOS", "0.5")
    eleicao = criar_aplicacao(0, tmp_path, ativar_eleicao=True).state.eleicao
    assert (eleicao.intervalo, eleicao.timeout) == (1.5, 0.5)


@pytest.mark.parametrize("valor", ["0", "-1", "nan", "inf", "um"])
def test_rejeita_tempos_invalidos(monkeypatch, valor):
    monkeypatch.setenv("BULLY_TIMEOUT_SEGUNDOS", valor)
    with pytest.raises(ValueError, match="número positivo"):
        _segundos_configurados("BULLY_TIMEOUT_SEGUNDOS", 1.0)
