"""Status de coordenação e mensagens autenticadas entre as agências."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from ..auth import agencia_autenticada
from ..config import NUMERO_AGENCIAS
from ..services.eleicao import BATIMENTO, VOTO

router = APIRouter(tags=["eleição"])
autenticacao_interna = [Depends(agencia_autenticada)]


class MensagemEleicao(BaseModel):
    origemAgencia: Annotated[int, Field(strict=True, ge=0, lt=NUMERO_AGENCIAS)]
    mandato: Annotated[int, Field(strict=True, ge=1)]


@router.get("/cluster/status")
async def status(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return request.app.state.eleicao.status()


@router.post(VOTO, dependencies=autenticacao_interna)
async def votar(dados: MensagemEleicao, request: Request):
    return request.app.state.eleicao.votar(dados.origemAgencia, dados.mandato)


@router.post(BATIMENTO, dependencies=autenticacao_interna)
async def batimento(dados: MensagemEleicao, request: Request):
    return request.app.state.eleicao.receber_batimento(dados.origemAgencia, dados.mandato)
