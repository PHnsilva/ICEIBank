"""Configurações compartilhadas pelas instâncias das agências."""

OFFSET = 78
NUMERO_AGENCIAS = 3
PORTA_BASE = 4000 + OFFSET

PORTAS_AGENCIAS = tuple(PORTA_BASE + agencia_id for agencia_id in range(NUMERO_AGENCIAS))
URLS_AGENCIAS = tuple(f"http://localhost:{porta}" for porta in PORTAS_AGENCIAS)


def agencia_responsavel(id_conta: int) -> int:
    """Retorna a agência responsável por uma conta usando particionamento modular."""
    return id_conta % NUMERO_AGENCIAS


def validar_agencia_id(agencia_id: int) -> int:
    """Valida e devolve um identificador de agência aceito pelo projeto."""
    if agencia_id < 0 or agencia_id >= NUMERO_AGENCIAS:
        raise ValueError(
            f"AGENCIA_ID deve estar entre 0 e {NUMERO_AGENCIAS - 1}; "
            f"valor recebido: {agencia_id}."
        )
    return agencia_id


def porta_da_agencia(agencia_id: int) -> int:
    """Retorna a porta HTTP reservada para uma agência válida."""
    return PORTAS_AGENCIAS[validar_agencia_id(agencia_id)]


def url_da_agencia(agencia_id: int) -> str:
    """Retorna a URL HTTP reservada para uma agência válida."""
    return URLS_AGENCIAS[validar_agencia_id(agencia_id)]
