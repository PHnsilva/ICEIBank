"""Eleição por maioria entre as agências, com mandatos e batimentos HTTP."""

import asyncio
import json
import logging
import os
import random
from pathlib import Path
from time import monotonic

import httpx

from ..auth import ConfiguracaoAuth, token_agencia
from ..config import NUMERO_AGENCIAS, porta_da_agencia

VOTO = "/interno/eleicao/voto"
BATIMENTO = "/interno/eleicao/batimento"
MAIORIA = NUMERO_AGENCIAS // 2 + 1
INTERVALO_BATIMENTO = 0.3
PRAZO_MAIORIA = 0.9
logger = logging.getLogger("uvicorn.error")


class Eleicao:
    def __init__(self, agencia_id: int, arquivo: Path, auth: ConfiguracaoAuth):
        self.agencia_id = agencia_id
        self.arquivo = arquivo
        self.auth = auth
        self.pares = [par for par in range(NUMERO_AGENCIAS) if par != agencia_id]
        self.mandato = 0
        self.voto = None
        try:
            estado = json.loads(arquivo.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        else:
            self.mandato = estado["mandato"]
            self.voto = estado["voto"]
            if (type(self.mandato) is not int or self.mandato < 0
                    or (self.voto is not None and
                        (type(self.voto) is not int or self.voto not in range(NUMERO_AGENCIAS)))):
                raise ValueError("Estado persistido da eleição inválido.")
        self.papel = "seguidora"
        self.lider = None
        self.ultima_maioria = 0.0
        self.protegido_ate = monotonic() + PRAZO_MAIORIA if self.mandato else 0.0
        self._renovar_prazo()

    def _renovar_prazo(self):
        self.prazo_eleicao = monotonic() + random.uniform(1.2, 2.0)

    def _gravar_voto(self, mandato, voto):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.arquivo.with_suffix(".tmp")
        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump({"mandato": mandato, "voto": voto}, arquivo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        temporario.replace(self.arquivo)
        self.mandato, self.voto = mandato, voto

    def _seguir(self, lider=None):
        if self.papel != "seguidora" or self.lider != lider:
            logger.info("Eleição agência %s: mandato %s, seguidora, líder %s",
                        self.agencia_id, self.mandato, lider)
        self.papel = "seguidora"
        self.lider = lider
        self._renovar_prazo()

    def _atualizar_mandato(self, mandato):
        if mandato > self.mandato:
            self._gravar_voto(mandato, None)
            self._seguir()

    def status(self):
        lider = self.lider
        agora = monotonic()
        if self.papel == "lider" and agora >= self.ultima_maioria + PRAZO_MAIORIA:
            lider = None
        elif self.papel == "seguidora" and agora >= self.prazo_eleicao:
            lider = None
        return {"agenciaId": self.agencia_id, "mandato": self.mandato,
                "papel": "seguidora" if lider is None and self.papel == "lider" else self.papel,
                "liderId": lider}

    def votar(self, origem, mandato):
        # Uma confirmação recente pode ainda sustentar o prazo de uma líder.
        protegido_ate = self.protegido_ate
        if self.papel == "lider":
            protegido_ate = max(protegido_ate, self.ultima_maioria + PRAZO_MAIORIA)
        if mandato > self.mandato and monotonic() < protegido_ate:
            return {"mandato": self.mandato, "aceito": False}
        self._atualizar_mandato(mandato)
        aceito = (mandato == self.mandato and self.voto in (None, origem)
                  and self.lider in (None, origem))
        if aceito:
            if self.voto is None:
                self._gravar_voto(mandato, origem)
            self._renovar_prazo()
            self.protegido_ate = monotonic() + PRAZO_MAIORIA
        return {"mandato": self.mandato, "aceito": aceito}

    def receber_batimento(self, origem, mandato):
        self._atualizar_mandato(mandato)
        aceito = (mandato == self.mandato and self.lider in (None, origem)
                  and self.papel != "lider")
        if aceito:
            self._seguir(origem)
            self.protegido_ate = monotonic() + PRAZO_MAIORIA
        return {"mandato": self.mandato, "aceito": aceito}

    async def _enviar(self, cliente, par, caminho, mandato):
        corpo = {"origemAgencia": self.agencia_id, "mandato": mandato}
        token = token_agencia(self.auth, self.agencia_id, par, caminho, corpo)
        try:
            resposta = await cliente.post(
                f"http://127.0.0.1:{porta_da_agencia(par)}{caminho}",
                json=corpo, headers={"Authorization": f"Bearer {token}"},
            )
            resposta.raise_for_status()
            dados = resposta.json()
            if isinstance(dados, dict) and type(dados.get("mandato")) is int:
                return dados
        except (httpx.HTTPError, ValueError):
            pass
        return {}

    async def _consultar_pares(self, cliente, caminho, mandato):
        respostas = await asyncio.gather(
            *(self._enviar(cliente, par, caminho, mandato) for par in self.pares)
        )
        self._atualizar_mandato(max(r.get("mandato", mandato) for r in respostas))
        return 1 + sum(r.get("aceito") is True and r["mandato"] == mandato for r in respostas)

    async def _disputar(self, cliente):
        mandato = self.mandato + 1
        self._gravar_voto(mandato, self.agencia_id)
        self.papel, self.lider = "candidata", None
        self._renovar_prazo()
        logger.info("Eleição agência %s: candidatura no mandato %s", self.agencia_id, mandato)
        inicio = monotonic()
        votos = await self._consultar_pares(cliente, VOTO, mandato)
        if (self.papel == "candidata" and self.mandato == mandato and votos >= MAIORIA
                and monotonic() < inicio + PRAZO_MAIORIA):
            self.papel, self.lider = "lider", self.agencia_id
            self.ultima_maioria = inicio
            logger.info("Eleição agência %s: eleita líder no mandato %s", self.agencia_id, mandato)

    async def executar(self):
        async with httpx.AsyncClient(timeout=0.25, trust_env=False) as cliente:
            while True:
                if self.papel == "lider":
                    inicio = monotonic()
                    if inicio >= self.ultima_maioria + PRAZO_MAIORIA:
                        self._seguir()
                        continue
                    mandato = self.mandato
                    confirmacoes = await self._consultar_pares(cliente, BATIMENTO, mandato)
                    if (self.papel == "lider" and self.mandato == mandato
                            and confirmacoes >= MAIORIA
                            and monotonic() < self.ultima_maioria + PRAZO_MAIORIA):
                        self.ultima_maioria = inicio
                    await asyncio.sleep(INTERVALO_BATIMENTO)
                elif monotonic() >= self.prazo_eleicao:
                    await self._disputar(cliente)
                else:
                    await asyncio.sleep(0.08)
