import pytest

from agencia.app.auth import ConfiguracaoAuth, token_agencia
from agencia.app.main import criar_aplicacao
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
