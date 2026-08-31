"""Relógio lógico de Lamport seguro para acesso por múltiplas threads."""

from threading import Lock


class RelogioLamport:
    """Mantém o contador lógico de uma única agência."""

    def __init__(self, valor_inicial: int = 0) -> None:
        if valor_inicial < 0:
            raise ValueError("O valor inicial do relógio não pode ser negativo.")
        self._contador = valor_inicial
        self._lock = Lock()

    @property
    def valor(self) -> int:
        """Obtém de forma segura o valor atual, sem avançar o relógio."""
        with self._lock:
            return self._contador

    def evento_local(self) -> int:
        """Avança o relógio para representar um evento puramente local."""
        with self._lock:
            self._contador += 1
            return self._contador

    def ao_enviar(self) -> int:
        """Avança o relógio imediatamente antes do envio de uma mensagem."""
        with self._lock:
            self._contador += 1
            return self._contador

    def ao_receber(self, timestamp_recebido: int) -> int:
        """Combina o relógio local com o timestamp recebido e o avança."""
        if timestamp_recebido < 0:
            raise ValueError("O timestamp recebido não pode ser negativo.")
        with self._lock:
            self._contador = max(self._contador, timestamp_recebido) + 1
            return self._contador
