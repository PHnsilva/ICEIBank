"""Processos e evidências isolados para apresentar as três versões reais."""

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import httpx
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parents[1]
VERSOES = {
    1: "21cfea62f23c6035d418556eb10fc3a6cde4bb25",
    2: "0d03c61cd96c17722eba6111cd0be8eca52ce938",
}


def esperar(condicao, timeout=35):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            resultado = condicao()
            if resultado:
                return resultado
        except (httpx.TransportError, KeyError):
            pass
        time.sleep(0.15)
    raise RuntimeError(
        "Estado esperado não observado. Consulte os logs desta execução."
    )


def fonte(sprint):
    return ROOT if sprint == 3 else ROOT / ".local/sprints" / str(sprint)


class Cluster:
    def __init__(self, sprint, codigo, dados):
        self.sprint, self.codigo, self.dados = (
            sprint,
            Path(codigo).resolve(),
            Path(dados).resolve(),
        )
        self.dados.mkdir(parents=True, exist_ok=True)
        self.processos, self.logs = {}, []
        self.gerencia, self.vhost = None, None
        self.cliente = httpx.Client(timeout=10, trust_env=False)
        self.env = {
            **os.environ,
            "JWT_SECRET": secrets.token_urlsafe(48),
            "AGENCIAS_JWT_SECRET": secrets.token_urlsafe(48),
            "LOGIN_USUARIO": "aluno",
            "LOGIN_SENHA_HASH": PasswordHash.recommended().hash("iceibank-sprint1"),
            "JWT_TTL_SECONDS": "3600",
            "BULLY_HEARTBEAT_SEGUNDOS": "1.5",
            "BULLY_TIMEOUT_SEGUNDOS": "0.5",
            "PYTHONIOENCODING": "utf-8",
        }
        for chave in list(self.env):
            if chave.lower().endswith("proxy"):
                self.env.pop(chave)
        self.env["NO_PROXY"] = "localhost,127.0.0.1"

    def __enter__(self):
        try:
            for porta in (4078, 4079, 4080):
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1", porta)) == 0:
                        raise RuntimeError(
                            f"Porta {porta} ocupada. Encerre a apresentação anterior."
                        )
            if self.sprint >= 2:
                url = os.environ.get(
                    "RABBITMQ_URL_TESTES", "amqp://guest:guest@127.0.0.1:5672/"
                )
                parsed = urlsplit(url)
                self.gerencia = httpx.Client(
                    base_url=os.environ.get(
                        "RABBITMQ_MANAGEMENT_URL_TESTES", "http://127.0.0.1:15672"
                    ),
                    auth=(
                        unquote(parsed.username or "guest"),
                        unquote(parsed.password or "guest"),
                    ),
                    trust_env=False,
                    timeout=15,
                )
                self.vhost = "iceibank-demo-" + secrets.token_hex(6)
                self.gerencia.put("/api/vhosts/" + self.vhost).raise_for_status()
                self.gerencia.put(
                    f"/api/permissions/{self.vhost}/{quote(unquote(parsed.username or 'guest'), safe='')}",
                    json={"configure": ".*", "write": ".*", "read": ".*"},
                ).raise_for_status()
                self.env["RABBITMQ_URL"] = urlunsplit(
                    parsed._replace(path="/" + self.vhost)
                )
            for agencia in range(3):
                self.iniciar(agencia)
            self.login()
            return self
        except BaseException:
            self.fechar()
            raise

    def iniciar(self, agencia):
        if agencia in self.processos and self.processos[agencia].poll() is None:
            raise RuntimeError("Processo já iniciado.")
        log = (self.dados / f"servidor-{agencia}.log").open("a", encoding="utf-8")
        self.logs.append(log)
        extra = ", ativar_eleicao=True" if self.sprint == 3 else ""
        codigo = (
            "from pathlib import Path; import uvicorn; from agencia.app.main import criar_aplicacao; "
            f"app=criar_aplicacao({agencia},Path({str(self.dados)!r}){extra}); "
            f"uvicorn.run(app,host='127.0.0.1',port={4078 + agencia},access_log=False)"
        )
        self.processos[agencia] = subprocess.Popen(
            [sys.executable, "-c", codigo],
            cwd=self.codigo,
            env=self.env,
            stdout=log,
            stderr=log,
        )
        esperar(
            lambda: (
                self.cliente.get(
                    f"http://127.0.0.1:{4078 + agencia}/config"
                ).status_code
                == 200
            )
        )

    def parar(self, agencia):
        processo = self.processos[agencia]
        if processo.poll() is None:
            processo.terminate()
            try:
                processo.wait(timeout=12)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait()

    def login(self):
        r = self.cliente.post(
            "http://127.0.0.1:4078/auth/login",
            json={"usuario": "aluno", "senha": "iceibank-sprint1"},
        )
        r.raise_for_status()
        self.cliente.headers["Authorization"] = "Bearer " + r.json()["access_token"]

    def api(self, metodo, agencia, caminho, corpo=None, esperado=200):
        r = self.cliente.request(
            metodo,
            f"http://127.0.0.1:{4078 + agencia}{caminho}",
            **({"json": corpo} if corpo is not None else {}),
        )
        registro = {
            "metodo": metodo,
            "agencia": agencia,
            "caminho": caminho,
            "pedido": corpo,
            "http": r.status_code,
            "resposta": r.json(),
        }
        with (self.dados / "requisicoes.ndjson").open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        if r.status_code != esperado:
            raise AssertionError(
                f"{metodo} {caminho}: HTTP {r.status_code}, esperado {esperado}: {r.text}"
            )
        return registro

    def criar(self, id, nome="Conta de demonstração", saldo="100.00"):
        return self.api(
            "POST",
            id % 3,
            "/contas",
            {"id": id, "nomeAluno": nome, "saldoInicial": saldo},
            201,
        )

    def saldo(self, id):
        return (
            self.cliente.get(f"http://127.0.0.1:{4078 + id % 3}/contas/{id}")
            .json()
            .get("saldo")
        )

    def lider(self, ids, lider):
        return all(
            self.cliente.get(f"http://127.0.0.1:{4078 + i}/bully/lider")
            .json()
            .get("liderAtual")
            == lider
            for i in ids
        )

    def fechar(self):
        for agencia in self.processos:
            self.parar(agencia)
        for log in self.logs:
            log.close()
        self.cliente.close()
        if self.gerencia is not None:
            try:
                if self.vhost:
                    self.gerencia.delete("/api/vhosts/" + self.vhost).raise_for_status()
            finally:
                self.gerencia.close()

    def __exit__(self, *_):
        self.fechar()


@contextmanager
def servidor_flutter(diretorio):
    class Silencioso(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    servidor = ThreadingHTTPServer(
        ("127.0.0.1", 8080),
        partial(Silencioso, directory=str(Path(diretorio).resolve())),
    )
    tarefa = threading.Thread(target=servidor.serve_forever, daemon=True)
    tarefa.start()
    try:
        yield
    finally:
        servidor.shutdown()
        servidor.server_close()
        tarefa.join()
