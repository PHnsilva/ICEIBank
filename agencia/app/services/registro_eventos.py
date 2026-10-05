"""Registro de eventos em arquivos JSON Lines separados por agência."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from ..config import validar_agencia_id
from .relogio_vetorial import validar_vetor


class RegistroEventos:
    """Acrescenta eventos ao log da agência com escrita protegida."""

    def __init__(self, agencia_id: int, diretorio_dados: Path | None = None) -> None:
        self.agencia_id = validar_agencia_id(agencia_id)
        self._diretorio_dados = diretorio_dados or Path(__file__).resolve().parents[2] / "data"
        self._caminho = self._diretorio_dados / f"eventos-agencia-{agencia_id}.jsonl"
        self._lock = Lock()
        self._historicos: dict[int, list[dict[str, Any]]] = {}

    @property
    def caminho(self) -> Path:
        """Informa o arquivo usado pelo registrador."""
        return self._caminho

    def registrar(
        self,
        tipo: str,
        timestamp_vetorial: list[int],
        detalhes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Grava um evento como um objeto JSON em uma única linha."""
        evento: dict[str, Any] = {
            "agencia": f"agencia-{self.agencia_id}",
            "tipo": tipo,
            "timestampVetorial": validar_vetor(timestamp_vetorial),
            "horaParede": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "detalhes": deepcopy(detalhes or {}),
        }
        linha = json.dumps(evento, ensure_ascii=False, separators=(",", ":"))

        with self._lock:
            self._diretorio_dados.mkdir(parents=True, exist_ok=True)
            with self._caminho.open("a", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(f"{linha}\n")
            # Indexa somente a conta efetivamente afetada por este evento.
            campo = {
                "TRANSFERENCIA_DEBITO": "idOrigem",
                "TRANSFERENCIA_CREDITO": "idDestino",
                "TRANSFERENCIA_CREDITO_REMOTO": "idDestino",
                "TRANSFERENCIA_FALHOU": "idOrigem",
            }.get(tipo, "idConta")
            id_conta = evento["detalhes"].get(campo)
            if type(id_conta) is int:
                self._historicos.setdefault(id_conta, []).append(deepcopy(evento))

        print(linha, flush=True)
        return evento

    def historico(self, id_conta: int, offset: int = 0, limite: int = 50) -> tuple[list[dict[str, Any]], int]:
        """Snapshot paginado do processo atual; logs de processos antigos não são saldos atuais."""
        with self._lock:
            eventos = self._historicos.get(id_conta, [])
            return deepcopy(eventos[offset:offset + limite]), len(eventos)
