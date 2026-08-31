"""Controlador HTTP das operações de contas."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request, status

from ..config import agencia_responsavel
from ..estado_agencia import Conta, EstadoAgencia
from ..schemas import CENTAVOS, ContaSaida, CriacaoConta, OperacaoValor, formatar_moeda

router = APIRouter(tags=["contas"])
IdContaRota = Annotated[int, Path(ge=0)]


def _estado(request: Request) -> EstadoAgencia:
    return request.app.state.estado_agencia


def _conta_saida(conta: Conta) -> ContaSaida:
    return ContaSaida(id=conta.id, nome_aluno=conta.nome_aluno, saldo=conta.saldo)


def _detalhes_conta(conta: Conta) -> dict[str, int | str]:
    return {
        "idConta": conta.id,
        "nomeAluno": conta.nome_aluno,
        "saldo": formatar_moeda(conta.saldo),
    }


@router.post("/contas", response_model=ContaSaida, status_code=status.HTTP_201_CREATED)
async def criar_conta(dados: CriacaoConta, request: Request) -> ContaSaida:
    """Cria uma conta quando esta instância é sua agência responsável."""
    estado = _estado(request)
    agencia_correta = agencia_responsavel(dados.id)
    if agencia_correta != estado.agencia_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A conta {dados.id} pertence à Agência {agencia_correta}, "
                f"não à Agência {estado.agencia_id}."
            ),
        )

    async with estado.lock:
        if dados.id in estado.contas:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A conta {dados.id} já existe nesta agência.",
            )

        conta = Conta(
            id=dados.id,
            nome_aluno=dados.nome_aluno,
            saldo=dados.saldo_inicial.quantize(CENTAVOS),
        )
        estado.contas[conta.id] = conta
        timestamp = estado.relogio.evento_local()
        estado.registro.registrar("CRIAR_CONTA", timestamp, _detalhes_conta(conta))
        return _conta_saida(conta)


@router.get("/contas/{id_conta}", response_model=ContaSaida)
async def consultar_conta(id_conta: IdContaRota, request: Request) -> ContaSaida:
    """Consulta uma conta armazenada na agência atual."""
    estado = _estado(request)
    async with estado.lock:
        conta = estado.contas.get(id_conta)
        if conta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A conta {id_conta} não foi encontrada nesta agência.",
            )
        return _conta_saida(conta)


@router.post("/contas/{id_conta}/depositar", response_model=ContaSaida)
async def depositar(
    id_conta: IdContaRota,
    operacao: OperacaoValor,
    request: Request,
) -> ContaSaida:
    """Deposita um valor positivo em uma conta local."""
    estado = _estado(request)
    async with estado.lock:
        conta = estado.contas.get(id_conta)
        if conta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A conta {id_conta} não foi encontrada nesta agência.",
            )

        valor = operacao.valor.quantize(CENTAVOS)
        conta.saldo += valor
        timestamp = estado.relogio.evento_local()
        estado.registro.registrar(
            "DEPOSITO",
            timestamp,
            {
                "idConta": conta.id,
                "valor": formatar_moeda(valor),
                "saldo": formatar_moeda(conta.saldo),
            },
        )
        return _conta_saida(conta)


@router.post("/contas/{id_conta}/sacar", response_model=ContaSaida)
async def sacar(
    id_conta: IdContaRota,
    operacao: OperacaoValor,
    request: Request,
) -> ContaSaida:
    """Saca um valor positivo quando há saldo suficiente."""
    estado = _estado(request)
    async with estado.lock:
        conta = estado.contas.get(id_conta)
        if conta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A conta {id_conta} não foi encontrada nesta agência.",
            )

        valor = operacao.valor.quantize(CENTAVOS)
        if conta.saldo < valor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Saldo insuficiente para realizar o saque.",
            )

        conta.saldo -= valor
        timestamp = estado.relogio.evento_local()
        estado.registro.registrar(
            "SAQUE",
            timestamp,
            {
                "idConta": conta.id,
                "valor": formatar_moeda(valor),
                "saldo": formatar_moeda(conta.saldo),
            },
        )
        return _conta_saida(conta)
