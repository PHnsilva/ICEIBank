import json

from agencia.app.services.relogio_vetorial import comparar_vetores
from scripts.ambiente_sprint2 import aguardar


def test_topologia_duravel_e_credito_vetorial(agencias, contas):
    ambiente = agencias["ambiente"]
    id, _ = contas
    if ambiente._gerencia is not None:
        filas = {fila["name"]: fila for fila in ambiente.filas()}
        for i in range(3):
            assert filas[f"fila-agencia-{i}"]["durable"] is True
            assert filas[f"fila-agencia-{i}"]["arguments"]["x-dead-letter-exchange"] == "iceibank.nao-processadas"
            assert filas[f"fila-agencia-{i}.nao-processadas"]["durable"] is True
        exchanges = ambiente._gerencia.get("/api/exchanges/" + ambiente.vhost).json()
        principal = next(e for e in exchanges if e["name"] == "iceibank.eventos")
        assert principal["type"] == "topic" and principal["durable"] is True
        bindings = ambiente._gerencia.get("/api/bindings/" + ambiente.vhost).json()
        for i in range(3):
            assert any(b["source"] == "iceibank.eventos" and b["destination"] == f"fila-agencia-{i}"
                       and b["routing_key"] == f"agencia.{i}.creditar" for b in bindings)
    r = ambiente.transferir(id, id+1, "7.50")
    assert r.status_code == 200 and r.json()["status"] == "publicada"
    assert "saldoDestino" not in r.json()
    aguardar(lambda: ambiente.saldo(id+1) == "107.50")
    h = ambiente.cliente.get(f"http://localhost:4079/contas/{id+1}/historico").json()
    recebido = h["eventos"][-1]
    assert recebido["tipo"] == "TRANSFERENCIA_CREDITO_REMOTO"
    assert recebido["detalhes"]["idTransferencia"] == r.json()["idTransferencia"]
    assert comparar_vetores(r.json()["vetorEnvio"], recebido["timestampVetorial"]) == "ANTES"


def test_destino_fora_do_ar_recebe_apos_reinicio_e_dlq_preserva(agencias, contas):
    ambiente = agencias["ambiente"]
    id, _ = contas
    ambiente.parar(1)
    r = ambiente.transferir(id, id+1, "8.00")
    assert r.status_code == 200
    assert ambiente.saldo(id) == "92.00"
    if ambiente._gerencia is not None:
        def retida():
            fila = ambiente._gerencia.get(f"/api/queues/{ambiente.vhost}/fila-agencia-1").json()
            return fila.get("messages_ready", 0) >= 1 and fila.get("consumers", -1) == 0
        aguardar(retida)
    ambiente.iniciar(1)
    assert ambiente.cliente.get(f"http://localhost:4079/contas/{id+1}").status_code == 404
    arquivo = ambiente.dados / "eventos-agencia-1.jsonl"
    aguardar(lambda: "CREDITO_REMOTO_FALHOU" in arquivo.read_text(encoding="utf-8"))
    eventos = [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines()]
    assert any(e["tipo"] == "CREDITO_REMOTO_FALHOU" and e["detalhes"]["idDestino"] == id+1 for e in eventos)
    if ambiente._gerencia is not None:
        mensagens = aguardar(lambda: [m for m in ambiente.mensagem_dlq(1)
            if json.loads(m["payload"])["idTransferencia"] == r.json()["idTransferencia"]])
        msg = next(m for m in mensagens if json.loads(m["payload"])["idTransferencia"] == r.json()["idTransferencia"])
        assert msg["properties"]["headers"]["x-death"][0]["reason"] == "rejected"
        assert msg["properties"]["delivery_mode"] == 2
    # Uma conta recriada não recebe silenciosamente o crédito que já foi para DLQ.
    ambiente.criar(id+1, "1.00")
    assert ambiente.saldo(id+1) == "1.00"
