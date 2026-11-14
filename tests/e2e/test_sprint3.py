from scripts.ambiente_sprint2 import aguardar


def test_bully_converge_para_maior_id_apos_falha_e_retorno(agencias):
    ambiente = agencias["ambiente"]

    def consenso(ids, lider):
        return all(
            ambiente.cliente.get(f"http://127.0.0.1:{4078 + agencia}/bully/lider").json()
            == {"idAgencia": agencia, "liderAtual": lider}
            for agencia in ids
        )

    aguardar(lambda: consenso((0, 1, 2), 2))
    ambiente.parar(2)
    try:
        aguardar(lambda: consenso((0, 1), 1))
        ambiente.parar(1)
        try:
            aguardar(lambda: consenso((0,), 0))
        finally:
            ambiente.iniciar(1)
        aguardar(lambda: consenso((0, 1), 1))
    finally:
        ambiente.iniciar(2)
    aguardar(lambda: consenso((0, 1, 2), 2))
