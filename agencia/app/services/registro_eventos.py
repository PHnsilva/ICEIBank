"""Registro de eventos em arquivos JSON Lines separados por agência."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from ..config import validar_agencia_id


class RegistroEventos:
    """Acrescenta eventos ao log da agência com escrita protegida."""

    def __init__(self, agencia_id: int, diretorio_dados: Path | None = None) -> None:
        self.agencia_id = validar_agencia_id(agencia_id)
        self._diretorio_dados = diretorio_dados or Path(__file__).resolve().parents[2] / "data"
        self._caminho = self._diretorio_dados / f"eventos-agencia-{agencia_id}.jsonl"
        self._lock = Lock()

    @property
    def caminho(self) -> Path:
        """Informa o arquivo usado pelo registrador."""
        return self._caminho

    def registrar(
        self,
        tipo: str,
        timestamp_lamport: int,
        detalhes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Grava um evento como um objeto JSON em uma única linha."""
        evento: dict[str, Any] = {
            "agencia": f"agencia-{self.agencia_id}",
            "tipo": tipo,
            "timestampLamport": timestamp_lamport,
            "horaParede": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "detalhes": detalhes or {},
        }
        linha = json.dumps(evento, ensure_ascii=False, separators=(",", ":"))

        with self._lock:
            self._diretorio_dados.mkdir(parents=True, exist_ok=True)
            with self._caminho.open("a", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(f"{linha}\n")

        print(linha, flush=True)
        return evento
