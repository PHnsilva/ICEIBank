"""Ponto de composição da aplicação FastAPI."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import validar_agencia_id
from .controllers.contas_controller import router as contas_router
from .estado_agencia import EstadoAgencia
from .services.registro_eventos import RegistroEventos
from .services.relogio_lamport import RelogioLamport


def _mensagem_validacao(tipo: str) -> str:
    mensagens = {
        "missing": "Campo obrigatório.",
        "greater_than": "O valor deve ser maior que zero.",
        "greater_than_equal": "O valor não pode ser negativo.",
        "string_too_short": "O texto não pode estar vazio.",
        "decimal_max_places": "Use no máximo duas casas decimais.",
        "decimal_max_digits": "O valor monetário é grande demais.",
        "int_parsing": "Informe um número inteiro válido.",
        "int_type": "Informe um número inteiro válido.",
        "decimal_parsing": "Informe um valor monetário válido.",
        "decimal_type": "Informe um valor monetário válido.",
        "json_invalid": "O corpo não contém um JSON válido.",
    }
    return mensagens.get(tipo, "Valor inválido.")


def criar_aplicacao(agencia_id: int, diretorio_dados: Path | None = None) -> FastAPI:
    """Cria uma aplicação isolada para a agência informada."""
    agencia_id = validar_agencia_id(agencia_id)
    app = FastAPI(
        title=f"ICEIBank — Agência {agencia_id}",
        version="0.1.0",
        description="Implementação acadêmica limitada às seções 1 a 10 da Sprint 1.",
    )
    app.state.estado_agencia = EstadoAgencia(
        agencia_id=agencia_id,
        relogio=RelogioLamport(),
        registro=RegistroEventos(agencia_id, diretorio_dados),
    )

    @app.exception_handler(RequestValidationError)
    async def tratar_erro_validacao(
        _request: Request,
        erro: RequestValidationError,
    ) -> JSONResponse:
        erros: list[dict[str, Any]] = []
        for item in erro.errors():
            localizacao = [str(parte) for parte in item["loc"] if parte not in {"body", "path"}]
            erros.append(
                {
                    "campo": ".".join(localizacao) or "corpo",
                    "mensagem": _mensagem_validacao(item["type"]),
                }
            )
        return JSONResponse(
            status_code=422,
            content={"detail": "Dados da requisição inválidos.", "erros": erros},
        )

    app.include_router(contas_router)
    return app
