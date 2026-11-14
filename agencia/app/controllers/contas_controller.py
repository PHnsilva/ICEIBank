"""Controlador HTTP das operações de contas."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Request, status

from fastapi.responses import JSONResponse

from ..config import agencia_responsavel
from ..estado_agencia import Conta, EstadoAgencia
from ..schemas import (
    CENTAVOS, ContaComVetor, ContaSaida, CriacaoConta, OperacaoPendente,
    OperacaoValor, TipoMovimentacao, formatar_moeda,
)
from ..services.relogio_vetorial import comparar_vetores

router = APIRouter(tags=["contas"])
IdContaRota = Annotated[int, Path(ge=0)]


def _estado(request: Request) -> EstadoAgencia:
    return request.app.state.estado_agencia


def _conta_saida(conta: Conta) -> ContaSaida:
    return ContaSaida(id=conta.id, nome_aluno=conta.nome_aluno, saldo=conta.saldo)


def _buscar_conta(estado: EstadoAgencia, id_conta: int) -> Conta:
    conta = estado.contas.get(id_conta)
    if conta is None:
        raise HTTPException(404, f"A conta {id_conta} não foi encontrada nesta agência.")
    return conta


def _snapshot(estado: EstadoAgencia, conta: Conta) -> ContaComVetor:
    return ContaComVetor(
        id=conta.id, nome_aluno=conta.nome_aluno, saldo=conta.saldo,
        vetor_atual=estado.relogio.valor, versao_agencia=estado.versao,
    )


def _movimentar(
    estado: EstadoAgencia, conta: Conta, tipo: TipoMovimentacao, valor: Decimal,
    *, operacao_id: UUID | None = None, offline: bool = False,
):
    valor = valor.quantize(CENTAVOS)
    if tipo == "SAQUE" and conta.saldo < valor:
        raise HTTPException(400, "Saldo insuficiente para realizar o saque.")
    saldo = conta.saldo + valor if tipo == "DEPOSITO" else conta.saldo - valor
    detalhes = {"idConta": conta.id, "valor": formatar_moeda(valor), "saldo": formatar_moeda(saldo)}
    if offline:
        detalhes["operacao"] = tipo
        if operacao_id is not None:
            detalhes["operacaoId"] = str(operacao_id)
    timestamp = estado.relogio.evento_local()
    estado.registro.registrar("SINCRONIZACAO_OFFLINE" if offline else tipo, timestamp, detalhes)
    conta.saldo = saldo


def _detalhes_conta(conta: Conta) -> dict[str, int | str]:
    return {
        "idConta": conta.id,
        "nomeAluno": conta.nome_aluno,
        "saldo": formatar_moeda(conta.saldo),
    }


@router.get("/contas/{id_conta}/historico")
async def consultar_historico(
    id_conta: IdContaRota,
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    """Histórico por conta, cronológico, do processo atual. Exige JWT de operador."""
    estado = _estado(request)
    async with estado.lock:
        conta = estado.contas.get(id_conta)
        if conta is None:
            raise HTTPException(404, f"A conta {id_conta} não foi encontrada nesta agência.")
        eventos, total = estado.registro.historico(id_conta, offset, limite)
        return {"idConta": id_conta, "saldoAtual": formatar_moeda(conta.saldo),
                "eventos": eventos, "total": total, "offset": offset, "limite": limite}


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


@router.get("/contas/{id_conta}", response_model=ContaComVetor)
async def consultar_conta(id_conta: IdContaRota, request: Request) -> ContaComVetor:
    """Lê o saldo e a versão correspondente do relógio sem avançá-lo."""
    estado = _estado(request)
    async with estado.lock:
        return _snapshot(estado, _buscar_conta(estado, id_conta))


@router.post("/contas/{id_conta}/depositar", response_model=ContaSaida)
async def depositar(
    id_conta: IdContaRota,
    operacao: OperacaoValor,
    request: Request,
) -> ContaSaida:
    """Deposita um valor positivo em uma conta local."""
    estado = _estado(request)
    async with estado.lock:
        conta = _buscar_conta(estado, id_conta)
        _movimentar(estado, conta, "DEPOSITO", operacao.valor)
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
        conta = _buscar_conta(estado, id_conta)
        _movimentar(estado, conta, "SAQUE", operacao.valor)
        return _conta_saida(conta)


@router.post("/contas/{id_conta}/sincronizar", response_model=ContaComVetor)
async def sincronizar(
    id_conta: IdContaRota,
    operacao: OperacaoPendente,
    request: Request,
):
    """Valida e aplica uma operação offline em uma única seção crítica."""
    estado = _estado(request)
    async with estado.lock:
        conta = _buscar_conta(estado, id_conta)
        chave = (id_conta, operacao.operacao_id) if operacao.operacao_id is not None else None
        anterior = estado.sincronizacoes.get(chave) if chave is not None else None
        if anterior is not None:
            pedido, resultado = anterior
            if pedido != operacao:
                raise HTTPException(400, "O identificador já pertence a outra operação.")
            return resultado

        snapshot = _snapshot(estado, conta)
        relacao = comparar_vetores(operacao.vetor_conhecido, snapshot.vetor_atual)
        reiniciada = operacao.versao_agencia not in (None, snapshot.versao_agencia)
        if relacao != "IGUAIS" or reiniciada:
            return JSONResponse(status_code=409, content={
                "detail": "O estado conhecido mudou. Revise a operação antes de enviá-la novamente.",
                "relacao": relacao,
                "vetorConhecido": operacao.vetor_conhecido,
                "vetorAtual": snapshot.vetor_atual,
                "contaAtual": snapshot.model_dump(mode="json", by_alias=True),
            })

        _movimentar(estado, conta, operacao.tipo, operacao.valor, operacao_id=operacao.operacao_id, offline=True)
        resultado = _snapshot(estado, conta)
        if chave is not None:
            estado.sincronizacoes[chave] = operacao, resultado
        return resultado
