"""Cria versões históricas isoladas; rode com o ambiente virtual ativo."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flutter", default="flutter", help="Executável do SDK Flutter 3.50.1"
    )
    parser.add_argument(
        "--sem-mobile", action="store_true", help="Prepara somente o backend"
    )
    args = parser.parse_args()
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements-demo.txt"],
        cwd=ROOT,
        check=True,
    )
    from scripts.ambiente_apresentacao import VERSOES, fonte

    for sprint, ref in VERSOES.items():
        pasta = fonte(sprint)
        if pasta.exists():
            atual = subprocess.check_output(
                ["git", "-C", str(pasta), "rev-parse", "HEAD"], text=True
            ).strip()
            if atual != ref:
                raise SystemExit(
                    f"{pasta} está em outra versão. Preserve os arquivos e escolha uma pasta limpa."
                )
        else:
            pasta.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(pasta), ref],
                cwd=ROOT,
                check=True,
            )
    if not args.sem_mobile:
        sdk = shutil.which(args.flutter)
        if sdk is None:
            raise SystemExit(
                "Instale Flutter 3.50.1 e informe --flutter /caminho/flutter."
            )
        sdk = str(Path(sdk).resolve())
        env = {**os.environ, "BOT": "true", "CI": "true"}
        subprocess.run(
            [sdk, "--disable-analytics"],
            cwd=ROOT / "app_mobile",
            env=env,
            check=True,
        )
        subprocess.run(
            [sdk, "pub", "get"],
            cwd=ROOT / "app_mobile",
            env=env,
            check=True,
        )
        subprocess.run(
            [
                sdk,
                "build",
                "web",
                "--release",
                "--no-web-resources-cdn",
                "--dart-define=ICEIBANK_HOST=127.0.0.1",
            ],
            cwd=ROOT / "app_mobile",
            env=env,
            check=True,
        )
    print(
        "Versões prontas. Inicie RabbitMQ; use python -m scripts.iniciar_apresentacao 1, 2 ou 3."
    )


if __name__ == "__main__":
    main()
