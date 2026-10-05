"""Estado volátil mantido por cada processo de agência."""

from asyncio import Lock
from dataclasses import dataclass
from decimal import Decimal


from .services.registro_eventos import RegistroEventos
from .services.relogio_vetorial import RelogioVetorial


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
        relogio: RelogioVetorial,
        registro: RegistroEventos,
    ) -> None:
        self.agencia_id = agencia_id
        self.relogio = relogio
        self.registro = registro
        self.contas: dict[int, Conta] = {}
        self.lock = Lock()
