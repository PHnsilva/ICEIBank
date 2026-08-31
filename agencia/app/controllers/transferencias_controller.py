"""Controlador das transferências locais e entre agências."""

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, HTTPException, Path, Request, status

from ..config import agencia_responsavel, url_da_agencia
from ..estado_agencia import EstadoAgencia
from ..schemas import (
    CENTAVOS,
    CreditoRemoto,
    TransferenciaSolicitada,
    formatar_moeda,
)

router = APIRouter(tags=["transferências"])
IdContaRota = Annotated[int, Path(ge=0)]


def _estado(request: Request) -> EstadoAgencia:
    return request.app.state.estado_agencia


def _detalhes_transferencia(
    id_origem: int,
    id_destino: int,
    valor: str,
    saldo: str,
) -> dict[str, int | str]:
    return {
        "idOrigem": id_origem,
        "idDestino": id_destino,
        "valor": valor,
        "saldo": saldo,
    }


async def _registrar_falha_remota(
    estado: EstadoAgencia,
    dados: TransferenciaSolicitada,
    valor_formatado: str,
    saldo_origem: str,
    agencia_destino: int,
    motivo: str,
) -> None:
    async with estado.lock:
        timestamp = estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_FALHOU",
            timestamp,
            {
                "idOrigem": dados.id_origem,
                "idDestino": dados.id_destino,
                "valor": valor_formatado,
                "saldoOrigem": saldo_origem,
                "agenciaDestino": agencia_destino,
                "motivo": motivo,
                "debitoAplicado": True,
            },
        )


def _erro_falha_remota(dados: TransferenciaSolicitada, valor: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            f"A transferência remota falhou. O débito de R$ {valor} já foi aplicado "
            f"à conta {dados.id_origem} e não foi restaurado. Esta é a inconsistência "
            "conhecida da Sprint 1, prevista para tratamento na Sprint 4."
        ),
    )


@router.post("/transferencias")
async def transferir(dados: TransferenciaSolicitada, request: Request) -> dict[str, Any]:
    """Debita a origem e credita um destino local ou remoto."""
    estado = _estado(request)
    valor = dados.valor.quantize(CENTAVOS)
    valor_formatado = formatar_moeda(valor)
    agencia_destino = agencia_responsavel(dados.id_destino)

    async with estado.lock:
        conta_origem = estado.contas.get(dados.id_origem)
        if conta_origem is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"A conta de origem {dados.id_origem} não foi encontrada na "
                    f"Agência {estado.agencia_id}. Envie a requisição à agência responsável."
                ),
            )
        if conta_origem.saldo < valor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Saldo insuficiente para realizar a transferência.",
            )

        conta_origem.saldo -= valor
        saldo_origem = formatar_moeda(conta_origem.saldo)
        timestamp_debito = estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_DEBITO",
            timestamp_debito,
            _detalhes_transferencia(
                dados.id_origem,
                dados.id_destino,
                valor_formatado,
                saldo_origem,
            ),
        )

        if agencia_destino == estado.agencia_id:
            conta_destino = estado.contas.get(dados.id_destino)
            if conta_destino is None:
                conta_origem.saldo += valor
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"A conta de destino {dados.id_destino} não foi encontrada. "
                        "O débito local foi restaurado."
                    ),
                )

            conta_destino.saldo += valor
            saldo_destino = formatar_moeda(conta_destino.saldo)
            timestamp_credito = estado.relogio.evento_local()
            estado.registro.registrar(
                "TRANSFERENCIA_CREDITO",
                timestamp_credito,
                _detalhes_transferencia(
                    dados.id_origem,
                    dados.id_destino,
                    valor_formatado,
                    saldo_destino,
                ),
            )
            return {
                "mensagem": "Transferência local realizada com sucesso.",
                "tipo": "local",
                "idOrigem": dados.id_origem,
                "idDestino": dados.id_destino,
                "valor": valor_formatado,
                "saldoOrigem": formatar_moeda(conta_origem.saldo),
                "saldoDestino": saldo_destino,
            }

    timestamp_envio = estado.relogio.ao_enviar()
    url = f"{url_da_agencia(agencia_destino)}/contas/{dados.id_destino}/creditar-remoto"
    corpo_remoto = {
        "valor": valor_formatado,
        "timestampLamport": timestamp_envio,
        "origemAgencia": estado.agencia_id,
    }

    try:
        async with httpx.AsyncClient(
            timeout=estado.timeout_http,
            transport=estado.transporte_http,
        ) as cliente:
            resposta = await cliente.post(url, json=corpo_remoto)
            resposta.raise_for_status()
            resposta_remota = resposta.json()
            if not isinstance(resposta_remota, dict) or "saldo" not in resposta_remota:
                raise ValueError("Resposta remota sem o saldo confirmado.")
            saldo_destino_remoto = resposta_remota["saldo"]
    except httpx.TimeoutException:
        motivo = "A agência de destino não respondeu dentro do limite de tempo."
        await _registrar_falha_remota(
            estado,
            dados,
            valor_formatado,
            saldo_origem,
            agencia_destino,
            motivo,
        )
        raise _erro_falha_remota(dados, valor_formatado) from None
    except httpx.HTTPStatusError as erro:
        motivo = f"A agência de destino respondeu com HTTP {erro.response.status_code}."
        await _registrar_falha_remota(
            estado,
            dados,
            valor_formatado,
            saldo_origem,
            agencia_destino,
            motivo,
        )
        raise _erro_falha_remota(dados, valor_formatado) from None
    except (httpx.RequestError, ValueError):
        motivo = "Não foi possível comunicar com a agência de destino."
        await _registrar_falha_remota(
            estado,
            dados,
            valor_formatado,
            saldo_origem,
            agencia_destino,
            motivo,
        )
        raise _erro_falha_remota(dados, valor_formatado) from None

    return {
        "mensagem": "Transferência entre agências realizada com sucesso.",
        "tipo": "entre-agencias",
        "idOrigem": dados.id_origem,
        "idDestino": dados.id_destino,
        "valor": valor_formatado,
        "saldoOrigem": saldo_origem,
        "saldoDestino": saldo_destino_remoto,
        "timestampEnvio": timestamp_envio,
    }


@router.post("/contas/{id_conta}/creditar-remoto")
async def creditar_remoto(
    id_conta: IdContaRota,
    credito: CreditoRemoto,
    request: Request,
) -> dict[str, int | str]:
    """Recebe o crédito enviado diretamente por outra agência."""
    estado = _estado(request)
    valor = credito.valor.quantize(CENTAVOS)

    async with estado.lock:
        timestamp = estado.relogio.ao_receber(credito.timestamp_lamport)
        conta = estado.contas.get(id_conta)
        if conta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A conta de destino {id_conta} não foi encontrada nesta agência.",
            )

        conta.saldo += valor
        saldo = formatar_moeda(conta.saldo)
        estado.registro.registrar(
            "TRANSFERENCIA_CREDITO_REMOTO",
            timestamp,
            {
                "idDestino": id_conta,
                "origemAgencia": credito.origem_agencia,
                "valor": formatar_moeda(valor),
                "saldo": saldo,
            },
        )
        return {"id": id_conta, "saldo": saldo, "timestampLamport": timestamp}
