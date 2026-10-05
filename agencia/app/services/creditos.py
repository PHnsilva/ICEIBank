"""Créditos recebidos pelo broker, sem rota HTTP ou JWT de usuário."""

from pydantic import ValidationError

from ..config import agencia_responsavel
from ..schemas import CreditoMensagem, formatar_moeda


async def processar_credito(estado, corpo) -> bool:
    try:
        credito = CreditoMensagem.model_validate(corpo)
        if (agencia_responsavel(credito.id_conta) != estado.agencia_id
                or credito.origem_agencia == estado.agencia_id
                or (credito.id_origem is not None
                    and agencia_responsavel(credito.id_origem) != credito.origem_agencia)):
            raise ValueError("Particionamento ou origem inválida.")
    except (ValidationError, ValueError):
        async with estado.lock:
            estado.registro.registrar("MENSAGEM_INVALIDA", estado.relogio.evento_local(),
                                      {"motivo": "Mensagem de crédito inválida."})
        return False

    async with estado.lock:
        vetor = estado.relogio.ao_receber(credito.vetor_envio)
        detalhes = {"idDestino": credito.id_conta, "idConta": credito.id_conta,
                    "idOrigem": credito.id_origem, "valor": formatar_moeda(credito.valor),
                    "origemAgencia": credito.origem_agencia,
                    "idTransferencia": credito.id_transferencia}
        conta = estado.contas.get(credito.id_conta)
        if conta is None:
            estado.registro.registrar("CREDITO_REMOTO_FALHOU", vetor,
                                      {**detalhes, "motivo": "conta não encontrada"})
            return False
        conta.saldo += credito.valor
        estado.registro.registrar("TRANSFERENCIA_CREDITO_REMOTO", vetor,
                                  {**detalhes, "saldo": formatar_moeda(conta.saldo)})
        return True
