"""Gera segredos locais; nunca substitui uma configuração existente."""
from pathlib import Path
import secrets

from pwdlib import PasswordHash

destino = Path(__file__).resolve().parents[1] / ".env"
with destino.open("x", encoding="utf-8") as arquivo:
    arquivo.write(
        f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
        f"AGENCIAS_JWT_SECRET={secrets.token_urlsafe(48)}\n"
        "LOGIN_USUARIO=aluno\n"
        f"LOGIN_SENHA_HASH='{PasswordHash.recommended().hash('iceibank-sprint1')}'\n"
        "JWT_TTL_SECONDS=900\n"
    )
print(".env criado. Login acadêmico local: aluno / iceibank-sprint1")
