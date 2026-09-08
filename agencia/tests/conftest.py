import pytest
from pwdlib import PasswordHash

HASH_TESTE = PasswordHash.recommended().hash("senha-teste")


@pytest.fixture(autouse=True)
def ambiente_auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "usuario-teste-" * 4)
    monkeypatch.setenv("AGENCIAS_JWT_SECRET", "agencias-teste-" * 4)
    monkeypatch.setenv("LOGIN_USUARIO", "aluno")
    monkeypatch.setenv("LOGIN_SENHA_HASH", HASH_TESTE)
    monkeypatch.setenv("JWT_TTL_SECONDS", "900")
