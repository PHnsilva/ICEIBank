"""Inicia as três agências da sprint escolhida; Ctrl+C encerra só seus processos."""

import argparse
import time
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from scripts.ambiente_apresentacao import ROOT, Cluster, fonte, servidor_flutter


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sprint", type=int, choices=[1, 2, 3])
    p.add_argument("--flutter-web", type=Path, default=ROOT / "app_mobile/build/web")
    args = p.parse_args()
    if not fonte(args.sprint).exists():
        p.error("Execute python -m scripts.preparar_apresentacao primeiro.")
    if args.sprint == 3 and not (args.flutter_web / "index.html").exists():
        p.error("Compile o Flutter Web antes de iniciar a Sprint 3.")
    dados = (
        ROOT
        / ".local/apresentacao"
        / datetime.now(UTC).strftime("ensaio-%Y%m%dT%H%M%S%f")
    )
    with Cluster(args.sprint, fonte(args.sprint), dados) as cluster:
        for id, nome in enumerate(["Ana", "Carla", "Diego", "Bruno"]):
            cluster.criar(id, nome)
        with servidor_flutter(args.flutter_web) if args.sprint == 3 else nullcontext():
            print(
                f"Sprint {args.sprint}: http://127.0.0.1:4078 (agências nas portas 4078–4080)",
                flush=True,
            )
            print(
                "Login: aluno / iceibank-sprint1 | contas 0, 1, 2, 3 com R$ 100,00",
                flush=True,
            )
            if args.sprint == 3:
                print("Cliente Flutter: http://127.0.0.1:8080", flush=True)
            print(f"Logs: {dados}\nCtrl+C para encerrar.", flush=True)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
