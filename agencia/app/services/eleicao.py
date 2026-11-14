"""Eleição Bully e verificação periódica da líder conhecida."""
import asyncio
import logging

import httpx

from ..auth import ConfiguracaoAuth, token_agencia
from ..config import NUMERO_AGENCIAS, porta_da_agencia
from ..estado_agencia import EstadoAgencia

ELEICAO = "/bully/eleicao"
COORDENADOR = "/bully/coordenador"
LIDER = "/bully/lider"
INTERVALO_HEARTBEAT = 3.0
TIMEOUT_HTTP = 1.0
logger = logging.getLogger("uvicorn.error")


class Eleicao:
    def __init__(self, estado: EstadoAgencia, auth: ConfiguracaoAuth):
        self.estado = estado
        self.agencia_id = estado.agencia_id
        self.auth = auth
        self.pares = tuple(par for par in range(NUMERO_AGENCIAS) if par != self.agencia_id)
        self.maiores = tuple(par for par in self.pares if par > self.agencia_id)
        self.lider: int | None = None
        self.solicitada = asyncio.Event()

    def status(self):
        return {"idAgencia": self.agencia_id, "liderAtual": self.lider}

    def _registrar(self, tipo, **detalhes):
        vetor = self.estado.relogio.evento_local()
        self.estado.registro.registrar(tipo, vetor, detalhes)

    def receber_eleicao(self, origem, vetor_envio):
        vetor = self.estado.relogio.ao_receber(vetor_envio)
        self.estado.registro.registrar("ELEICAO_RECEBIDA", vetor, {"de": origem, "minhaId": self.agencia_id})
        self.solicitada.set()

    def receber_coordenador(self, lider, vetor_envio):
        vetor = self.estado.relogio.ao_receber(vetor_envio)
        aceito = lider > self.agencia_id and (self.lider is None or lider >= self.lider)
        self.estado.registro.registrar("LIDER_ANUNCIADO", vetor, {"liderId": lider, "aceito": aceito})
        if aceito:
            self.lider = lider
        elif lider < self.agencia_id:
            self.solicitada.set()

    async def _enviar(self, cliente, par, caminho, campo):
        corpo = {campo: self.agencia_id, "vetorEnvio": self.estado.relogio.ao_enviar()}
        token = token_agencia(self.auth, self.agencia_id, par, caminho, corpo)
        try:
            resposta = await cliente.post(
                f"http://127.0.0.1:{porta_da_agencia(par)}{caminho}",
                json=corpo, headers={"Authorization": f"Bearer {token}"},
            )
            return resposta.status_code == 200
        except httpx.RequestError:
            return False

    async def _disputar(self, cliente):
        self._registrar("ELEICAO_INICIADA", idAgencia=self.agencia_id)
        # As rotas e esta tarefa usam o mesmo event loop. Um anúncio recebido
        # enquanto esperamos HTTP tem prioridade sobre a resposta da sondagem.
        lider_anterior = self.lider
        respostas = await asyncio.gather(*(
            self._enviar(cliente, par, ELEICAO, "origemId") for par in self.maiores
        ))
        if any(respostas):
            if self.lider == self.agencia_id:
                self.lider = None
            return
        if self.lider != lider_anterior and self.lider is not None:
            return
        if self.lider != self.agencia_id:
            self.lider = self.agencia_id
            self._registrar("TORNOU_LIDER", idAgencia=self.agencia_id)
            logger.info("Bully: agência %s tornou-se líder", self.agencia_id)
        await asyncio.gather(*(
            self._enviar(cliente, par, COORDENADOR, "liderId") for par in self.pares
        ))

    async def _consultar(self, cliente, par):
        try:
            resposta = await cliente.get(f"http://127.0.0.1:{porta_da_agencia(par)}{LIDER}")
            resposta.raise_for_status()
            dados = resposta.json()
            if isinstance(dados, dict) and dados.get("idAgencia") == par:
                return dados
        except (httpx.HTTPError, ValueError):
            pass
        return None

    async def _verificar(self, cliente):
        lider = self.lider
        if lider is None:
            await self._disputar(cliente)
        elif lider == self.agencia_id:
            # Recupera a prioridade de uma agência maior caso seu anúncio
            # de retorno tenha sido perdido.
            respostas = await asyncio.gather(*(self._consultar(cliente, par) for par in self.maiores))
            if any(respostas) and self.lider == lider:
                await self._disputar(cliente)
        else:
            resposta = await self._consultar(cliente, lider)
            if self.lider == lider and (resposta is None or resposta.get("liderAtual") != lider):
                self.lider = None
                self._registrar("LIDER_NAO_RESPONDEU", liderAtual=lider, agencia=self.agencia_id)
                await self._disputar(cliente)

    async def executar(self):
        self.solicitada.set()
        async with httpx.AsyncClient(timeout=TIMEOUT_HTTP, trust_env=False) as cliente:
            while True:
                try:
                    await asyncio.wait_for(self.solicitada.wait(), timeout=INTERVALO_HEARTBEAT)
                except TimeoutError:
                    await self._verificar(cliente)
                else:
                    self.solicitada.clear()
                    await self._disputar(cliente)
