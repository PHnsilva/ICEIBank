"""Pub/Sub RabbitMQ assíncrono, integrado ao ciclo de vida do FastAPI."""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import aio_pika

from ..config import NUMERO_AGENCIAS

EXCHANGE = "iceibank.eventos"


class FalhaPublicacao(RuntimeError):
    """A publicação não foi confirmada; seu resultado pode ser incerto."""


class MensageriaRabbitMQ:
    def __init__(self, url: str) -> None:
        if not url or urlsplit(url).scheme not in {"amqp", "amqps"}:
            raise ValueError("Defina RABBITMQ_URL com a URL AMQP/AMQPS do RabbitMQ.")
        self._url = url
        self._conexao = None
        self._exchange = None

    @classmethod
    def do_ambiente(cls):
        return cls(os.environ.get("RABBITMQ_URL", ""))

    async def iniciar(self, agencia_id: int, processar: Callable[[dict], Awaitable[bool]]) -> None:
        try:
            self._conexao = await aio_pika.connect_robust(self._url, timeout=10)
            publicador = await self._conexao.channel(publisher_confirms=True, on_return_raises=True)
            self._exchange = await publicador.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
            consumidor = await self._conexao.channel()
            await consumidor.set_qos(prefetch_count=1)
            filas = []
            # Todas as filas existem antes de publicar, inclusive destinos que nunca subiram.
            for id_fila in range(NUMERO_AGENCIAS):
                fila = await consumidor.declare_queue(f"fila-agencia-{id_fila}", durable=True)
                await fila.bind(EXCHANGE, routing_key=f"agencia.{id_fila}.creditar")
                filas.append(fila)

            async def receber(mensagem):
                try:
                    corpo = json.loads(mensagem.body)
                except (ValueError, UnicodeDecodeError):
                    corpo = None
                try:
                    aplicado = await processar(corpo)
                except Exception:
                    await mensagem.reject(requeue=False)
                    print(f"[Agência {agencia_id}] Falha interna ao processar mensagem.", flush=True)
                    return
                if aplicado:
                    await mensagem.ack()
                else:
                    await mensagem.reject(requeue=False)

            await filas[agencia_id].consume(receber, no_ack=False)
            print(f"[Agência {agencia_id}] RabbitMQ: exchange topic {EXCHANGE}; consumidor ativo.", flush=True)
        except Exception:
            await self.fechar()
            raise RuntimeError("Não foi possível iniciar a mensageria. Confira RABBITMQ_URL e o broker.") from None

    async def publicar(self, routing_key: str, mensagem: dict) -> None:
        if self._exchange is None:
            raise FalhaPublicacao("Mensageria indisponível.")
        try:
            # Confirmação do broker prova publicação, não aplicação do crédito.
            await asyncio.wait_for(self._exchange.publish(
                aio_pika.Message(
                    json.dumps(mensagem, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=mensagem.get("idTransferencia"),
                ), routing_key=routing_key, mandatory=True, timeout=5,
            ), timeout=6)
        except Exception:
            raise FalhaPublicacao("O broker não confirmou a publicação.") from None

    async def fechar(self) -> None:
        if self._conexao is not None:
            await self._conexao.close()
            self._conexao = None
        self._exchange = None
