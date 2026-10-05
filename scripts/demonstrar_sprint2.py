"""Demonstrações reais do roteiro. Execute a partir da raiz com python -m scripts.demonstrar_sprint2."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from agencia.app.services.relogio_vetorial import comparar_vetores
from agencia.mesclar_logs import carregar_eventos, pares_concorrentes
from scripts.ambiente_sprint2 import AmbienteSprint2, ROOT, aguardar


def mostrar_eventos(dados):
    for i in range(3):
        arquivo = dados / f"eventos-agencia-{i}.jsonl"
        if not arquivo.exists():
            continue
        print(f"--- Log real da Agência {i} ---")
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            e = json.loads(linha)
            d = e["detalhes"]
            conta = d.get("idOrigem") if e["tipo"] == "TRANSFERENCIA_DEBITO" else d.get("idConta", d.get("idDestino"))
            print(f"[{e['agencia']}] vetor={e['timestampVetorial']} {e['tipo']} "
                  f"conta={conta} "
                  f"valor={d.get('valor', '-')} saldo={d.get('saldo', '-')} motivo={d.get('motivo', '-')}")


def demonstrar(cenario, saida):
    dados = saida / ("execucao-" + cenario + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
    resultado = {"cenario": cenario, "verificadoEmUTC": datetime.now(timezone.utc).isoformat()}
    with AmbienteSprint2(dados) as ambiente:
        ambiente.criar(0)
        ambiente.criar(1)
        if cenario in {"resiliencia", "adicional"}:
            ambiente.parar(1)
            print("Agência 1 encerrada após criar a conta 1 (saldo 100.00).")
        r = ambiente.transferir(0, 1, "15.00")
        assert r.status_code == 200 and r.json()["status"] == "publicada"
        print(f"POST /transferencias: HTTP {r.status_code}; status={r.json()['status']}; saldoOrigem={r.json()['saldoOrigem']}")
        print("Resposta confirma publicação; não confirma crédito no destino.")
        resultado["respostaTransferencia"] = r.json()
        if cenario in {"transferencia", "causal"}:
            aguardar(lambda: ambiente.saldo(1) == "115.00")
            resultado["saldoDestino"] = ambiente.saldo(1)
            print("GET Agência 1 /contas/1: saldo=115.00; crédito assíncrono confirmado pela consulta.")
            eventos = carregar_eventos(dados)
            credito = next(e for e in eventos if e["tipo"] == "TRANSFERENCIA_CREDITO_REMOTO")
            debito = next(e for e in eventos if e["tipo"] == "TRANSFERENCIA_DEBITO")
            assert comparar_vetores(debito["timestampVetorial"], credito["timestampVetorial"]) == "ANTES"
            resultado["debitoAntesCredito"] = True
            if cenario == "causal":
                assert list(pares_concorrentes(eventos))
                resultado["paresConcorrentes"] = len(list(pares_concorrentes(eventos)))
                print("\nExecutando: python agencia/mesclar_logs.py --dados <logs desta execução>")
                subprocess.run([sys.executable, str(ROOT / "agencia/mesclar_logs.py"), "--dados", str(dados)], check=True)
                print("\nConferência: débito [2, 0, 0] ANTES do crédito [3, 2, 0]; este par não é concorrente.")
            else:
                mostrar_eventos(dados)
        else:
            def retida():
                fila = ambiente._gerencia.get(f"/api/queues/{ambiente.vhost}/fila-agencia-1").json()
                return fila if fila.get("messages_ready", 0) == 1 and fila.get("consumers", -1) == 0 else None
            aguardar(retida)
            print("RabbitMQ: fila-agencia-1 retém 1 mensagem, com zero consumidores.")
            ambiente.iniciar(1)
            status_conta = ambiente.cliente.get("http://localhost:4079/contas/1").status_code
            assert status_conta == 404
            print("Agência 1 reiniciada. GET /contas/1: HTTP 404 (conta em memória foi perdida).")
            dlq = aguardar(lambda: ambiente.mensagem_dlq(1))
            corpo = json.loads(dlq[0]["payload"])
            assert corpo["idTransferencia"] == r.json()["idTransferencia"]
            assert dlq[0]["properties"]["headers"]["x-death"][0]["reason"] == "rejected"
            assert dlq[0]["properties"]["delivery_mode"] == 2
            mostrar_eventos(dados)
            print("RabbitMQ: fila-agencia-1.nao-processadas preserva o crédito de 15.00 após falhas.")
            print("x-death.reason=rejected; mensagem entregue, mas conta ausente; saldo da origem=85.00.")
            resultado.update({"contaAposReinicioHTTP": status_conta, "mensagemNaDLQ": corpo,
                              "motivoDeadLetter": "rejected", "deliveryMode": dlq[0]["properties"]["delivery_mode"]})
            if cenario == "adicional":
                ambiente.criar(1, "1.00")
                assert ambiente.saldo(1) == "1.00"
                print("Conta 1 recriada: saldo=1.00; mensagem na DLQ não é reaplicada automaticamente.")
                resultado["saldoContaRecriada"] = "1.00"
        resultado["topologia"] = [{"nome": f["name"], "duravel": f["durable"], "argumentos": f["arguments"]}
                                   for f in ambiente.filas()]
        (saida / f"{cenario}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nVerificações do cenário: OK. Os processos e o vhost exclusivos do ensaio foram encerrados.")
    return dados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cenario", choices=["transferencia", "resiliencia", "causal", "adicional"])
    parser.add_argument("--saida", type=Path, default=ROOT / "evidencias/sprint2")
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    demonstrar(args.cenario, args.saida)
