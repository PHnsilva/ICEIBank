"""Estado volátil mantido por cada processo de agência."""

from asyncio import Lock
from dataclasses import dataclass
from decimal import Decimal

import httpx

from .services.registro_eventos import RegistroEventos
from .services.relogio_lamport import RelogioLamport


@dataclass
class Conta:
    """Conta bancária armazenada somente em memória."""

    id: int
    nome_aluno: str
    saldo: Decimal


class EstadoAgencia:
    """Agrupa os recursos exclusivos de uma instância da aplicação."""

    def __init__(
        self,
        agencia_id: int,
        relogio: RelogioLamport,
        registro: RegistroEventos,
        transporte_http: httpx.AsyncBaseTransport | None = None,
        timeout_http: float = 3.0,
    ) -> None:
        self.agencia_id = agencia_id
        self.relogio = relogio
        self.registro = registro
        self.transporte_http = transporte_http
        self.timeout_http = timeout_http
        self.contas: dict[int, Conta] = {}
        self.lock = Lock()
