"""Esquemas de entrada e saída da API REST."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer

CENTAVOS = Decimal("0.01")
IdConta = Annotated[int, Field(strict=True, ge=0)]
SaldoInicial = Annotated[Decimal, Field(ge=0, max_digits=16, decimal_places=2)]
ValorPositivo = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=2)]


def formatar_moeda(valor: Decimal) -> str:
    """Representa um valor monetário com exatamente duas casas decimais."""
    return f"{valor.quantize(CENTAVOS):.2f}"


class EsquemaBase(BaseModel):
    """Configuração comum para nomes internos em português e aliases da API."""

    model_config = ConfigDict(populate_by_name=True)


class CriacaoConta(EsquemaBase):
    """Dados necessários para criar uma conta."""

    id: IdConta
    nome_aluno: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        alias="nomeAluno"
    )
    saldo_inicial: SaldoInicial = Field(alias="saldoInicial")


class OperacaoValor(EsquemaBase):
    """Valor de um depósito ou saque."""

    valor: ValorPositivo


class TransferenciaSolicitada(EsquemaBase):
    """Dados de uma transferência iniciada pela agência da conta de origem."""

    id_origem: IdConta = Field(alias="idOrigem")
    id_destino: IdConta = Field(alias="idDestino")
    valor: ValorPositivo


class CreditoMensagem(EsquemaBase):
    """Crédito assíncrono recebido da exchange topic."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    valor: ValorPositivo
    id_conta: IdConta = Field(alias="idConta")
    id_origem: IdConta | None = Field(default=None, alias="idOrigem")
    vetor_envio: list[Annotated[int, Field(strict=True, ge=0)]] = Field(alias="vetorEnvio", min_length=3, max_length=3)
    id_transferencia: str | None = Field(default=None, alias="idTransferencia", max_length=100)
    origem_agencia: Annotated[int, Field(strict=True, ge=0, le=2)] = Field(
        alias="origemAgencia"
    )


class ContaSaida(EsquemaBase):
    """Representação pública de uma conta e seu saldo atual."""

    id: int
    nome_aluno: str = Field(alias="nomeAluno")
    saldo: Decimal

    @field_serializer("saldo")
    def serializar_saldo(self, saldo: Decimal) -> str:
        return formatar_moeda(saldo)
