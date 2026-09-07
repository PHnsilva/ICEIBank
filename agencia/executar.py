"""Inicializador de uma agência a partir da variável AGENCIA_ID."""

import os
from pathlib import Path

from dotenv import load_dotenv

import uvicorn

from app.config import porta_da_agencia, validar_agencia_id
from app.main import criar_aplicacao


def obter_agencia_id() -> int:
    """Lê e valida a agência selecionada no ambiente."""
    valor = os.getenv("AGENCIA_ID")
    if valor is None:
        raise ValueError("Defina AGENCIA_ID com um valor entre 0 e 2.")
    try:
        agencia_id = int(valor)
    except ValueError as erro:
        raise ValueError("AGENCIA_ID deve ser um número inteiro entre 0 e 2.") from erro
    return validar_agencia_id(agencia_id)


def main() -> None:
    """Inicia o servidor HTTP na porta reservada para a agência."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        agencia_id = obter_agencia_id()
        app = criar_aplicacao(agencia_id)
    except ValueError as erro:
        raise SystemExit(f"Erro de configuração: {erro}") from None

    porta = porta_da_agencia(agencia_id)
    print(f"Iniciando Agência {agencia_id} em http://localhost:{porta}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=porta)


if __name__ == "__main__":
    main()
