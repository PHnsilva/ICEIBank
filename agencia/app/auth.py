"""Autenticação de operadores e mensagens entre agências, com chaves separadas."""

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

router = APIRouter(tags=["autenticação"])
bearer = HTTPBearer(auto_error=False)
senhas = PasswordHash.recommended()


@dataclass(frozen=True)
class ConfiguracaoAuth:
    segredo_usuario: str
    segredo_agencias: str
    usuario: str
    senha_hash: str
    validade_segundos: int = 900

    @classmethod
    def do_ambiente(cls):
        config = cls(
            os.environ.get("JWT_SECRET", ""),
            os.environ.get("AGENCIAS_JWT_SECRET", ""),
            os.environ.get("LOGIN_USUARIO", ""),
            os.environ.get("LOGIN_SENHA_HASH", ""),
            int(os.environ.get("JWT_TTL_SECONDS", "900")),
        )
        if (min(len(config.segredo_usuario), len(config.segredo_agencias)) < 32
                or config.segredo_usuario == config.segredo_agencias
                or not config.usuario or not config.senha_hash.startswith("$argon2id$")
                or not 1 <= config.validade_segundos <= 86400):
            raise ValueError("Configure .env com chaves distintas (32+ caracteres), usuário, hash Argon2id e TTL de 1 a 86400 segundos.")
        return config


def emitir_token(segredo: str, sujeito: str, audiencia: str, validade: int, **claims) -> str:
    agora = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode(
        {**claims, "sub": sujeito, "iss": "iceibank", "aud": audiencia,
         "iat": agora, "nbf": agora, "exp": agora + validade},
        segredo, algorithm="HS256",
    )


def erro_401(mensagem="Token ausente ou inválido."):
    return HTTPException(401, mensagem, headers={"WWW-Authenticate": "Bearer"})


def validar_token(token: str, segredo: str, audiencia: str) -> dict:
    try:
        return jwt.decode(token, segredo, algorithms=["HS256"], audience=audiencia,
                          issuer="iceibank", options={"require": ["sub", "iss", "aud", "exp", "iat", "nbf"]})
    except jwt.ExpiredSignatureError:
        raise erro_401("Token expirado. Faça login novamente.") from None
    except jwt.InvalidTokenError:
        raise erro_401() from None


def usuario_autenticado(
    request: Request,
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if credencial is None:
        raise erro_401()
    config = request.app.state.auth
    claims = validar_token(credencial.credentials, config.segredo_usuario, "iceibank-api")
    if claims.get("tipo") != "usuario" or claims["sub"] != config.usuario:
        raise erro_401()
    return claims


def resumo_mensagem(caminho: str, corpo: dict) -> str:
    mensagem = caminho + "\n" + json.dumps(corpo, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(mensagem.encode()).hexdigest()


def token_agencia(config: ConfiguracaoAuth, origem: int, destino: int, caminho: str, corpo: dict):
    return emitir_token(config.segredo_agencias, f"agencia-{origem}", f"agencia-{destino}", 30,
                        tipo="agencia", mensagem=resumo_mensagem(caminho, corpo))


async def agencia_autenticada(
    request: Request,
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credencial is None:
        raise erro_401()
    estado = request.app.state.estado_agencia
    claims = validar_token(credencial.credentials, request.app.state.auth.segredo_agencias,
                           f"agencia-{estado.agencia_id}")
    corpo = await request.json()
    origem = corpo.get("origemAgencia")
    if (type(origem) is not int or origem not in range(3) or origem == estado.agencia_id
            or claims.get("tipo") != "agencia" or claims["sub"] != f"agencia-{origem}"
            or not hmac.compare_digest(str(claims.get("mensagem", "")), resumo_mensagem(request.url.path, corpo))):
        raise erro_401("Credencial da agência não corresponde à mensagem.")
    return claims


class Login(BaseModel):
    usuario: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=1024)


@router.post("/auth/login")
def login(dados: Login, request: Request):
    config = request.app.state.auth
    # Verifica o hash mesmo quando o usuário não existe para não revelar esse fato pelo tempo.
    senha_valida = senhas.verify(dados.senha, config.senha_hash)
    if not senha_valida or not hmac.compare_digest(dados.usuario.encode(), config.usuario.encode()):
        raise erro_401("Usuário ou senha inválidos.")
    token = emitir_token(config.segredo_usuario, config.usuario, "iceibank-api",
                         config.validade_segundos, tipo="usuario")
    from fastapi.responses import JSONResponse
    return JSONResponse({"access_token": token, "token_type": "bearer",
                         "expires_in": config.validade_segundos},
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
