"""Transferência local síncrona ou publicação de crédito remoto pelo RabbitMQ."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import usuario_autenticado
from ..config import agencia_responsavel
from ..schemas import CENTAVOS, TransferenciaSolicitada, formatar_moeda
from ..services.mensageria import FalhaPublicacao

router = APIRouter(tags=["transferências"])


@router.post("/transferencias", dependencies=[Depends(usuario_autenticado)])
async def transferir(dados: TransferenciaSolicitada, request: Request) -> dict[str, Any]:
    estado = request.app.state.estado_agencia
    valor = dados.valor.quantize(CENTAVOS)
    destino = agencia_responsavel(dados.id_destino)
    id_transferencia = str(uuid4())
    detalhes = {"idOrigem": dados.id_origem, "idDestino": dados.id_destino,
                "valor": formatar_moeda(valor), "idTransferencia": id_transferencia}
    async with estado.lock:
        origem = estado.contas.get(dados.id_origem)
        if origem is None:
            raise HTTPException(404, "Conta de origem não encontrada nesta agência. Envie à agência responsável.")
        if origem.saldo < valor:
            raise HTTPException(400, "Saldo insuficiente para realizar a transferência.")
        origem.saldo -= valor
        estado.registro.registrar("TRANSFERENCIA_DEBITO", estado.relogio.evento_local(),
                                  {**detalhes, "saldo": formatar_moeda(origem.saldo)})
        resultado = {**detalhes, "saldoOrigem": formatar_moeda(origem.saldo)}
        if destino == estado.agencia_id:
            conta_destino = estado.contas.get(dados.id_destino)
            if conta_destino is None:
                origem.saldo += valor
                estado.registro.registrar("ESTORNO_LOCAL", estado.relogio.evento_local(),
                    {**detalhes, "idConta": origem.id, "saldo": formatar_moeda(origem.saldo)})
                raise HTTPException(404, "Conta de destino não encontrada. O débito local foi restaurado.")
            conta_destino.saldo += valor
            estado.registro.registrar("TRANSFERENCIA_CREDITO", estado.relogio.evento_local(),
                                      {**detalhes, "saldo": formatar_moeda(conta_destino.saldo)})
            return {**resultado, "tipo": "local", "status": "concluida",
                    "mensagem": "Transferência local realizada com sucesso.",
                    "saldoDestino": formatar_moeda(conta_destino.saldo)}

        vetor_envio = estado.relogio.ao_enviar()
        mensagem = {"idConta": dados.id_destino, "idOrigem": dados.id_origem,
                    "valor": formatar_moeda(valor), "vetorEnvio": vetor_envio,
                    "origemAgencia": estado.agencia_id, "idTransferencia": id_transferencia}
        try:
            await request.app.state.mensageria.publicar(f"agencia.{destino}.creditar", mensagem)
        except FalhaPublicacao:
            estado.registro.registrar("TRANSFERENCIA_FALHOU", estado.relogio.evento_local(),
                {**detalhes, "saldoOrigem": formatar_moeda(origem.saldo), "debitoAplicado": True,
                 "motivo": "publicação não confirmada pelo broker"})
            raise HTTPException(502, "O broker não confirmou a publicação. O débito já foi aplicado e não foi restaurado; consulte o histórico antes de repetir.") from None
        estado.registro.registrar("TRANSFERENCIA_PUBLICADA", vetor_envio,
                                  {**detalhes, "agenciaDestino": destino})
        return {**resultado, "tipo": "entre-agencias", "status": "publicada",
                "vetorEnvio": vetor_envio,
                "mensagem": "Transferência publicada para a agência de destino (entrega assíncrona)."}
