"""Testes reais em três processos. Recusa portas ocupadas e usa dados temporários."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx
import pytest
from playwright.sync_api import sync_playwright
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def agencias(tmp_path_factory):
    for porta in (4078, 4079, 4080):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", porta)) == 0:
                pytest.fail(f"Porta {porta} ocupada. Encerre a agência local antes do teste isolado.")
    pasta = tmp_path_factory.mktemp("agencias-e2e")
    env = {**os.environ, "JWT_SECRET": secrets.token_urlsafe(48),
           "AGENCIAS_JWT_SECRET": secrets.token_urlsafe(48), "LOGIN_USUARIO": "aluno",
           "LOGIN_SENHA_HASH": PasswordHash.recommended().hash("senha-e2e"),
           "JWT_TTL_SECONDS": "900", "PYTHONIOENCODING": "utf-8"}
    processos, logs = [], []
    try:
        for i in range(3):
            log = (pasta / f"servidor-{i}.log").open("w", encoding="utf-8")
            logs.append(log)
            codigo = ("from pathlib import Path; import uvicorn; from agencia.app.main import criar_aplicacao; "
                      f"uvicorn.run(criar_aplicacao({i}, Path({str(pasta)!r})), host='127.0.0.1', port={4078+i})")
            processos.append(subprocess.Popen([sys.executable, "-c", codigo], cwd=ROOT,
                env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        with httpx.Client(timeout=1) as c:
            for i in range(3):
                limite = time.monotonic() + 30
                while True:
                    try:
                        if c.get(f"http://localhost:{4078+i}/config").status_code == 200: break
                    except httpx.TransportError: pass
                    if time.monotonic() > limite: pytest.fail(f"Agência {i} não iniciou; veja {pasta}")
                    time.sleep(.1)
        yield {"env": env, "dados": pasta}
    finally:
        for p in processos: p.terminate()
        for p in processos: p.wait(timeout=10)
        for log in logs: log.close()


@pytest.fixture(scope="session")
def navegador(agencias):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(navegador):
    context = navegador.new_context(viewport={"width": 1365, "height": 1080}, locale="pt-BR")
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def contas(request, agencias):
    # Identificadores distintos por teste; todas as operações continuam em memória.
    base = (list(request.session.items).index(request.node) + 1) * 30
    with httpx.Client() as c:
        token = c.post("http://localhost:4078/auth/login", json={"usuario": "aluno", "senha": "senha-e2e"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        for id in (base, base+1, base+2, base+3):
            r = c.post(f"http://localhost:{4078+id%3}/contas", json={"id": id, "nomeAluno": f"Aluno {id}", "saldoInicial": "100.00"})
            assert r.status_code == 201
        yield base, c
