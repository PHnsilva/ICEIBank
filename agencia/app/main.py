"""Ponto de composição da aplicação FastAPI."""

from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import URLS_AGENCIAS, PORTAS_AGENCIAS, validar_agencia_id
from .auth import ConfiguracaoAuth, router as auth_router, usuario_autenticado
from .controllers.contas_controller import router as contas_router
from .controllers.transferencias_controller import router as transferencias_router
from .estado_agencia import EstadoAgencia
from .services.registro_eventos import RegistroEventos
from .services.relogio_vetorial import RelogioVetorial
from .services.mensageria import MensageriaRabbitMQ
from .services.creditos import processar_credito


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


def criar_aplicacao(
    agencia_id: int,
    diretorio_dados: Path | None = None,
    mensageria=None,
) -> FastAPI:
    """Cria uma aplicação isolada para a agência informada."""
    agencia_id = validar_agencia_id(agencia_id)
    broker = mensageria if mensageria is not None else MensageriaRabbitMQ.do_ambiente()

    @asynccontextmanager
    async def lifespan(app):
        try:
            await broker.iniciar(agencia_id, lambda corpo: processar_credito(app.state.estado_agencia, corpo))
            yield
        finally:
            await broker.fechar()

    app = FastAPI(
        title=f"ICEIBank — Agência {agencia_id}",
        version="0.2.0",
        description="Sistema bancário distribuído acadêmico — Sprint 2.",
        lifespan=lifespan,
    )
    app.state.auth = ConfiguracaoAuth.do_ambiente()
    app.state.mensageria = broker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[*URLS_AGENCIAS, *[f"http://127.0.0.1:{p}" for p in PORTAS_AGENCIAS]],
        allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"],
    )
    app.state.estado_agencia = EstadoAgencia(
        agencia_id=agencia_id,
        relogio=RelogioVetorial(agencia_id),
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

    app.include_router(auth_router)
    resposta_401 = {401: {"description": "Token ausente, inválido, expirado ou inadequado à operação."}}
    app.include_router(contas_router, dependencies=[Depends(usuario_autenticado)], responses=resposta_401)
    app.include_router(transferencias_router, responses=resposta_401)

    frontend = Path(__file__).resolve().parents[1] / "frontend"
    app.mount("/static", StaticFiles(directory=frontend), name="static")

    @app.get("/", include_in_schema=False)
    def pagina_inicial():
        return FileResponse(frontend / "index.html", headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; connect-src 'self' " + " ".join(URLS_AGENCIAS) + "; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        })

    @app.get("/config", tags=["configuração"])
    def configuracao_publica():
        return {"agenciaAtual": agencia_id, "agencias": [
            {"id": i, "url": url} for i, url in enumerate(URLS_AGENCIAS)
        ]}

    return app
