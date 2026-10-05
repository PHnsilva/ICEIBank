"""Relógio vetorial de uma agência; snapshots não expõem o estado interno."""

from threading import Lock


def validar_vetor(vetor: list[int], tamanho: int = 3) -> list[int]:
    if (not isinstance(vetor, list) or len(vetor) != tamanho
            or any(type(valor) is not int or valor < 0 for valor in vetor)):
        raise ValueError(f"O vetor deve conter {tamanho} inteiros não negativos.")
    return list(vetor)


class RelogioVetorial:
    def __init__(self, id_agencia: int, numero_agencias: int = 3) -> None:
        if (type(numero_agencias) is not int or numero_agencias < 1
                or type(id_agencia) is not int or not 0 <= id_agencia < numero_agencias):
            raise ValueError("Identificador ou número de agências inválido.")
        self.id_agencia = id_agencia
        self._vetor = [0] * numero_agencias
        self._lock = Lock()

    @property
    def valor(self) -> list[int]:
        with self._lock:
            return list(self._vetor)

    def evento_local(self) -> list[int]:
        with self._lock:
            self._vetor[self.id_agencia] += 1
            return list(self._vetor)

    def ao_enviar(self) -> list[int]:
        return self.evento_local()

    def ao_receber(self, vetor_recebido: list[int]) -> list[int]:
        recebido = validar_vetor(vetor_recebido, len(self._vetor))
        with self._lock:
            self._vetor = [max(local, remoto) for local, remoto in zip(self._vetor, recebido)]
            self._vetor[self.id_agencia] += 1
            return list(self._vetor)


def comparar_vetores(v1: list[int], v2: list[int]) -> str:
    primeiro = validar_vetor(v1, len(v1))
    segundo = validar_vetor(v2, len(primeiro))
    menor = all(a <= b for a, b in zip(primeiro, segundo))
    maior = all(b <= a for a, b in zip(primeiro, segundo))
    if menor and maior:
        return "IGUAIS"
    if menor:
        return "ANTES"
    if maior:
        return "DEPOIS"
    return "CONCORRENTES"
