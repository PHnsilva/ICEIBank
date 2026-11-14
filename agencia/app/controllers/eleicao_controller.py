"""Consulta pública da líder e mensagens autenticadas do Bully."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth import agencia_autenticada
from ..config import NUMERO_AGENCIAS
from ..schemas import Vetor
from ..services.eleicao import COORDENADOR, ELEICAO, LIDER

router = APIRouter(tags=["eleição"])
autenticacao_interna = [Depends(agencia_autenticada)]
IdAgencia = Annotated[int, Field(strict=True, ge=0, lt=NUMERO_AGENCIAS)]


class MensagemBully(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vetorEnvio: Vetor


class MensagemEleicao(MensagemBully):
    origemId: IdAgencia


class MensagemCoordenador(MensagemBully):
    liderId: IdAgencia


@router.get(LIDER)
async def lider(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return request.app.state.eleicao.status()


@router.post(ELEICAO, dependencies=autenticacao_interna)
async def receber_eleicao(dados: MensagemEleicao, request: Request):
    eleicao = request.app.state.eleicao
    if dados.origemId >= eleicao.agencia_id:
        raise HTTPException(400, "A eleição deve ser enviada para uma agência de ID maior.")
    eleicao.receber_eleicao(dados.origemId, dados.vetorEnvio)
    return {"ok": True}


@router.post(COORDENADOR, dependencies=autenticacao_interna)
async def receber_coordenador(dados: MensagemCoordenador, request: Request):
    request.app.state.eleicao.receber_coordenador(dados.liderId, dados.vetorEnvio)
    return {"ok": True}
