from scripts.ambiente_sprint2 import aguardar


def test_reeleicao_apos_falha_da_lider_e_retorno(agencias):
    ambiente = agencias["ambiente"]

    def url(agencia, caminho):
        return f"http://127.0.0.1:{4078 + agencia}{caminho}"

    def status(agencia):
        return ambiente.cliente.get(url(agencia, "/cluster/status")).json()

    def consenso(agencias):
        visoes = [status(agencia) for agencia in agencias]
        lideres = [visao for visao in visoes if visao["papel"] == "lider"]
        if len(lideres) == 1 and all(
            visao["liderId"] == lideres[0]["agenciaId"]
            and visao["mandato"] == lideres[0]["mandato"]
            for visao in visoes
        ):
            return lideres[0]

    resposta = ambiente.cliente.post(
        url(0, "/interno/eleicao/voto"), json={"origemAgencia": 1, "mandato": 999}
    )
    assert resposta.status_code == 401
    todas = {0, 1, 2}
    inicial = aguardar(lambda: consenso(todas))
    antiga = inicial["agenciaId"]
    restantes = todas - {antiga}
    ambiente.parar(antiga)
    try:
        nova = aguardar(lambda: consenso(restantes))
        assert nova["agenciaId"] in restantes
        assert nova["mandato"] > inicial["mandato"]
    finally:
        ambiente.iniciar(antiga)
    assert aguardar(lambda: consenso(todas)) == nova

    paradas = todas - {nova["agenciaId"]}
    for agencia in paradas:
        ambiente.parar(agencia)
    try:
        aguardar(lambda: status(nova["agenciaId"])["liderId"] is None)
    finally:
        for agencia in paradas:
            ambiente.iniciar(agencia)
