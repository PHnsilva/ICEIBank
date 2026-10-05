"""Ambiente real de teste: cria apenas seu vhost e encerra apenas seus processos."""

import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parents[1]


def aguardar(condicao, timeout=20):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            resultado = condicao()
            if resultado:
                return resultado
        except httpx.TransportError:
            pass
        time.sleep(.1)
    raise AssertionError("O estado esperado não foi observado dentro do prazo.")


class AmbienteSprint2:
    def __init__(self, dados: Path):
        self.dados = dados
        self.dados.mkdir(parents=True, exist_ok=True)
        url = os.environ.get("RABBITMQ_URL_TESTES", "")
        if not url:
            raise ValueError("Defina RABBITMQ_URL_TESTES para um broker/vhost exclusivo de testes.")
        self._gerencia = None
        self.vhost = None
        gerencia_url = os.environ.get("RABBITMQ_MANAGEMENT_URL_TESTES")
        if gerencia_url:
            parsed = urlsplit(url)
            self._gerencia = httpx.Client(base_url=gerencia_url, timeout=10,
                auth=(unquote(parsed.username or "guest"), unquote(parsed.password or "guest")))
            self.vhost = "iceibank-testes-" + secrets.token_hex(6)
            r = self._gerencia.put("/api/vhosts/" + self.vhost)
            if r.status_code not in (201, 204):
                self._gerencia.close()
                self._gerencia = None
                raise ValueError("Não foi possível criar um vhost isolado. Confira as credenciais de teste.")
            r = self._gerencia.put(f"/api/permissions/{self.vhost}/{quote(unquote(parsed.username or 'guest'), safe='')}",
                                   json={"configure": ".*", "write": ".*", "read": ".*"})
            if r.status_code not in (201, 204):
                self.fechar()
                raise ValueError("Não foi possível conceder acesso ao vhost de teste.")
            url = urlunsplit(parsed._replace(path="/" + self.vhost))
        self.url = url
        self.env = {**os.environ, "RABBITMQ_URL": url,
                    "JWT_SECRET": secrets.token_urlsafe(48), "AGENCIAS_JWT_SECRET": secrets.token_urlsafe(48),
                    "LOGIN_USUARIO": "aluno", "LOGIN_SENHA_HASH": PasswordHash.recommended().hash("senha-e2e"),
                    "JWT_TTL_SECONDS": "900", "PYTHONIOENCODING": "utf-8"}
        self.processos = {}
        self.logs = []
        self.cliente = httpx.Client(timeout=10)

    def __enter__(self):
        try:
            for porta in (4078, 4079, 4080):
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1", porta)) == 0:
                        raise ValueError(f"Porta {porta} ocupada. Encerre a agência manual antes dos testes.")
            for agencia in range(3):
                self.iniciar(agencia)
            r = self.cliente.post("http://localhost:4078/auth/login", json={"usuario": "aluno", "senha": "senha-e2e"})
            r.raise_for_status()
            self.cliente.headers["Authorization"] = "Bearer " + r.json()["access_token"]
            return self
        except Exception:
            self.fechar()
            raise

    def iniciar(self, agencia):
        if agencia in self.processos and self.processos[agencia].poll() is None:
            raise ValueError("Agência de teste já iniciada.")
        log = (self.dados / f"servidor-{agencia}.log").open("a", encoding="utf-8")
        self.logs.append(log)
        codigo = ("from pathlib import Path; import uvicorn; from agencia.app.main import criar_aplicacao; "
                  f"uvicorn.run(criar_aplicacao({agencia}, Path({str(self.dados)!r})), host='127.0.0.1', port={4078+agencia}, access_log=False)")
        self.processos[agencia] = subprocess.Popen([sys.executable, "-c", codigo], cwd=ROOT,
            env=self.env, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with httpx.Client(timeout=1) as c:
            aguardar(lambda: c.get(f"http://localhost:{4078+agencia}/config").status_code == 200, timeout=30)

    def parar(self, agencia):
        processo = self.processos[agencia]
        if processo.poll() is None:
            processo.terminate()
            processo.wait(timeout=10)

    def criar(self, id, saldo="100.00"):
        r = self.cliente.post(f"http://localhost:{4078+id%3}/contas",
            json={"id": id, "nomeAluno": f"Aluno {id}", "saldoInicial": saldo})
        assert r.status_code == 201
        return r.json()

    def saldo(self, id):
        return self.cliente.get(f"http://localhost:{4078+id%3}/contas/{id}").json().get("saldo")

    def transferir(self, origem, destino, valor):
        return self.cliente.post(f"http://localhost:{4078+origem%3}/transferencias",
            json={"idOrigem": origem, "idDestino": destino, "valor": valor})

    def filas(self):
        if self._gerencia is None:
            raise ValueError("Inspeção das filas requer RABBITMQ_MANAGEMENT_URL_TESTES.")
        r = self._gerencia.get("/api/queues/" + self.vhost)
        r.raise_for_status()
        return r.json()

    def mensagem_dlq(self, agencia):
        r = self._gerencia.post(f"/api/queues/{self.vhost}/fila-agencia-{agencia}.nao-processadas/get",
            json={"count": 100, "ackmode": "ack_requeue_true", "encoding": "auto"})
        r.raise_for_status()
        return r.json()

    def fechar(self):
        for agencia in getattr(self, "processos", {}):
            self.parar(agencia)
        for log in getattr(self, "logs", []):
            log.close()
        if hasattr(self, "cliente"):
            self.cliente.close()
        if self._gerencia is not None:
            # Exclusivamente o vhost aleatório criado por este objeto.
            if self.vhost and self.vhost.startswith("iceibank-testes-"):
                self._gerencia.delete("/api/vhosts/" + self.vhost).raise_for_status()
            self._gerencia.close()
            self._gerencia = None

    def __exit__(self, *args):
        self.fechar()
