"""Linha do tempo vetorial, apresentada por hora de parede e comparada por causalidade."""

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from agencia.app.services.relogio_vetorial import comparar_vetores, validar_vetor
except ModuleNotFoundError:
    from app.services.relogio_vetorial import comparar_vetores, validar_vetor

CABECALHO = "=== Linha do tempo (ordenada por hora de parede) ==="


def carregar_eventos(pasta: Path | None = None) -> list[dict]:
    pasta = pasta or Path(__file__).resolve().parent / "data"
    eventos = []
    legados = 0
    for arquivo in sorted(pasta.glob("*.jsonl")):
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if not linha.strip():
                continue
            try:
                evento = json.loads(linha)
                # Lamport preservado da Sprint 1 não contém informação para comparar vetores.
                if "timestampVetorial" not in evento and "timestampLamport" in evento:
                    legados += 1
                    continue
                validar_vetor(evento["timestampVetorial"])
                datetime.fromisoformat(evento["horaParede"].replace("Z", "+00:00"))
                if evento["agencia"] not in {"agencia-0", "agencia-1", "agencia-2"}:
                    raise ValueError("Agência inválida.")
                if not isinstance(evento["detalhes"], dict) or not isinstance(evento["tipo"], str):
                    raise ValueError("Campos inválidos.")
                eventos.append(evento)
            except (ValueError, KeyError, TypeError):
                raise ValueError(f"Evento inválido em {arquivo.name}, linha {numero}.") from None
    if legados:
        print(f"Aviso: {legados} eventos Lamport da Sprint 1 preservados e excluídos da análise vetorial.")
    return sorted(eventos, key=lambda e: datetime.fromisoformat(e["horaParede"].replace("Z", "+00:00")))


def pares_concorrentes(eventos):
    for i, primeiro in enumerate(eventos):
        for segundo in eventos[i + 1:]:
            if (primeiro["agencia"] != segundo["agencia"]
                    and comparar_vetores(primeiro["timestampVetorial"], segundo["timestampVetorial"]) == "CONCORRENTES"):
                yield primeiro, segundo


def imprimir_linha_do_tempo(eventos) -> None:
    eventos = list(eventos)
    print(CABECALHO)
    if not eventos:
        print("Nenhum evento foi encontrado nos logs das agências.")
    for evento in eventos:
        print(f"[{evento['agencia']}] vetor={evento['timestampVetorial']} {evento['tipo']} "
              f"parede={evento['horaParede']} detalhes={json.dumps(evento['detalhes'], ensure_ascii=False, sort_keys=True)}")
    print("\n=== Pares de eventos CONCORRENTES entre agências diferentes ===")
    encontrou = False
    for e1, e2 in pares_concorrentes(eventos):
        encontrou = True
        print(f"[{e1['agencia']}] {e1['tipo']} ({e1['timestampVetorial']}) x "
              f"[{e2['agencia']}] {e2['tipo']} ({e2['timestampVetorial']})")
    if not encontrou:
        print("(nenhum par concorrente encontrado nesta execução)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, help="Diretório de logs desta execução (evita misturar reinícios).")
    args = parser.parse_args()
    try:
        imprimir_linha_do_tempo(carregar_eventos(args.dados))
    except (ValueError, OSError) as erro:
        raise SystemExit(str(erro)) from None


if __name__ == "__main__":
    main()
