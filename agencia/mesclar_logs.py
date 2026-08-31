"""Mescla os logs JSONL das agências em uma linha do tempo de Lamport."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

CABECALHO = "=== Linha do tempo unificada (ordenada por relogio de Lamport) ==="
DIRETORIO_DADOS = Path(__file__).resolve().parent / "data"


def carregar_eventos(diretorio_dados: Path = DIRETORIO_DADOS) -> list[dict[str, Any]]:
    """Lê todos os arquivos JSONL e devolve seus eventos em ordem lógica."""
    eventos: list[dict[str, Any]] = []
    for caminho in sorted(diretorio_dados.glob("*.jsonl")):
        with caminho.open("r", encoding="utf-8") as arquivo:
            for numero_linha, linha in enumerate(arquivo, start=1):
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    evento = json.loads(linha)
                    int(evento["timestampLamport"])
                    str(evento["horaParede"])
                    str(evento["agencia"])
                    str(evento["tipo"])
                    detalhes = evento["detalhes"]
                    if not isinstance(detalhes, dict):
                        raise TypeError
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
                    raise ValueError(
                        f"Evento inválido em {caminho.name}, linha {numero_linha}."
                    ) from erro
                eventos.append(evento)

    return sorted(
        eventos,
        key=lambda evento: (
            int(evento["timestampLamport"]),
            str(evento["horaParede"]),
            str(evento["agencia"]),
        ),
    )


def imprimir_linha_do_tempo(eventos: Iterable[dict[str, Any]]) -> None:
    """Imprime todos os eventos, destacando timestamps Lamport empatados."""
    eventos_ordenados = list(eventos)
    contagens = Counter(int(evento["timestampLamport"]) for evento in eventos_ordenados)

    print(CABECALHO)
    if not eventos_ordenados:
        print("Nenhum evento foi encontrado nos logs das agências.")
        return

    for evento in eventos_ordenados:
        timestamp = int(evento["timestampLamport"])
        marca_empate = f" [EMPATE x{contagens[timestamp]}]" if contagens[timestamp] > 1 else ""
        detalhes = json.dumps(evento["detalhes"], ensure_ascii=False, sort_keys=True)
        print(
            f"L={timestamp:04d}{marca_empate} | "
            f"parede={evento['horaParede']} | "
            f"agencia={evento['agencia']} | "
            f"tipo={evento['tipo']} | "
            f"detalhes={detalhes}"
        )


def main() -> None:
    """Executa a leitura e a exibição da linha do tempo unificada."""
    try:
        eventos = carregar_eventos()
    except OSError as erro:
        raise SystemExit(f"Erro ao ler os logs: {erro}") from None
    except ValueError as erro:
        raise SystemExit(f"Erro ao mesclar os logs: {erro}") from None
    imprimir_linha_do_tempo(eventos)


if __name__ == "__main__":
    main()
