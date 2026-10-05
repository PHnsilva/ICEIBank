import pytest
from pwdlib import PasswordHash

HASH_TESTE = PasswordHash.recommended().hash("senha-teste")


class MensageriaTeste:
    """Dublê apenas da publicação; integração real é exercitada em tests/e2e."""

    def __init__(self):
        self.publicadas = []
        self.falhar = False

    @classmethod
    def do_ambiente(cls):
        return cls()

    async def iniciar(self, agencia_id, processar):
        self.processar = processar

    async def publicar(self, routing_key, mensagem):
        from agencia.app.services.mensageria import FalhaPublicacao
        if self.falhar:
            raise FalhaPublicacao("Falha de teste.")
        self.publicadas.append((routing_key, mensagem))

    async def fechar(self):
        pass


@pytest.fixture(autouse=True)
def ambiente_auth(monkeypatch):
    monkeypatch.setattr("agencia.app.main.MensageriaRabbitMQ", MensageriaTeste)
    monkeypatch.setenv("JWT_SECRET", "usuario-teste-" * 4)
    monkeypatch.setenv("AGENCIAS_JWT_SECRET", "agencias-teste-" * 4)
    monkeypatch.setenv("LOGIN_USUARIO", "aluno")
    monkeypatch.setenv("LOGIN_SENHA_HASH", HASH_TESTE)
    monkeypatch.setenv("JWT_TTL_SECONDS", "900")
