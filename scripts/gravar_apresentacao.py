"""Executa cenários reais e gera um MP4 legendado, sem faixa de áudio.

Uso: python -m scripts.gravar_apresentacao --chromium /caminho/chromium
RabbitMQ com Manager deve estar ativo. Não usa evidências históricas como execução nova.
"""

import argparse
import json
import re
import subprocess
import textwrap
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from scripts.ambiente_apresentacao import (
    ROOT,
    Cluster,
    esperar,
    fonte,
    servidor_flutter,
)

BG = "#0b1422"
INK = "#edf3fc"
MUTED = "#aebfd5"
TEAL = "#55ddc0"
FONT = Path("/usr/share/fonts/truetype/dejavu")


class Filme:
    def __init__(self, saida):
        self.saida = saida.resolve()
        self.saida.mkdir(parents=True, exist_ok=False)
        (self.saida / "paineis").mkdir()
        (self.saida / "originais").mkdir()
        (self.saida / "clipes").mkdir()
        self.paginas = {}
        self.atual = None
        self.cenas = []
        self.sprint = 0
        self.codigo = ROOT
        self.data = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")

    def font(self, size, mono=False, bold=False):
        nome = "DejaVuSansMono" if mono else "DejaVuSans"
        return ImageFont.truetype(
            str(FONT / (nome + ("-Bold" if bold else "") + ".ttf")), size
        )

    def texto(
        self, d, xy, texto, largura, size=28, fill=INK, mono=False, bold=False, espaco=9
    ):
        x, y = xy
        f = self.font(size, mono, bold)
        for paragrafo in str(texto).splitlines():
            linha = ""
            palavras = paragrafo.split(" ")
            for palavra in palavras:
                teste = (linha + " " + palavra).strip()
                if d.textlength(teste, font=f) > largura and linha:
                    d.text((x, y), linha, fill=fill, font=f)
                    y += size + espaco
                    linha = palavra
                else:
                    linha = teste
            d.text((x, y), linha, fill=fill, font=f)
            y += size + espaco
        return y

    def base(self, titulo, legenda):
        im = Image.new("RGB", (1920, 1080), BG)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1920, 7), fill=TEAL)
        d.text((45, 28), "ICEIBank", fill=TEAL, font=self.font(28, bold=True))
        d.text(
            (290, 31),
            f"SPRINT {self.sprint}",
            fill=MUTED,
            font=self.font(23),
        )
        d.text((45, 75), titulo, fill=INK, font=self.font(35, bold=True))
        d.rounded_rectangle((30, 866, 1890, 1040), radius=16, fill="#16283b")
        self.texto(d, (60, 887), legenda, 1780, size=31, espaco=11)
        d.text(
            (45, 1052),
            f"{self.data} • ICEIBank",
            fill=MUTED,
            font=self.font(17),
        )
        d.text(
            (1790, 1052), f"{len(self.cenas) + 1:02d}", fill=TEAL, font=self.font(19)
        )
        return im, d

    def trecho(
        self, im, d, caminho, busca, xy=(1340, 160), largura=510, linhas=16, size=19
    ):
        texto = (self.codigo / caminho).read_text(encoding="utf-8").splitlines()
        focos = {
            "async def criar_conta": "conta = Conta(",
            "async def depositar": "conta.saldo += valor",
            "async def sacar": "conta.saldo -= valor",
            "if agencia_destino == estado.agencia_id": "conta_destino.saldo += valor",
            "timestamp_envio =": "resposta = await cliente.post(",
        }
        foco = focos.get(busca)
        if foco and any(foco in linha for linha in texto):
            busca = foco
        inicio = next(i for i, linha in enumerate(texto) if busca in linha)
        x, y = xy
        caminho_visivel = "\n".join(
            textwrap.wrap(
                caminho, width=max(25, int(largura / 13)), break_long_words=True
            )
        )
        y = self.texto(
            d, (x, y), caminho_visivel, largura, size=21, fill=TEAL, mono=True
        )
        d.text(
            (x, y + 5),
            f"Linha {inicio + 1}",
            fill=MUTED,
            font=self.font(18),
        )
        y += 42
        f = self.font(size, mono=True)
        for i, linha in enumerate(texto[inicio : inicio + linhas], inicio + 1):
            for j, parte in enumerate(
                textwrap.wrap(
                    linha.expandtabs(4),
                    width=max(30, int(largura / (size * 0.61)) - 5),
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
                or [""]
            ):
                if y > 825:
                    return inicio + 1
                d.text(
                    (x, y),
                    f"{i:3d} {parte}" if j == 0 else "    " + parte,
                    font=f,
                    fill=TEAL
                    if j == 0 and ("def " in linha or "class " in linha)
                    else INK,
                )
                y += size + 5
        return inicio + 1

    def registrar_pagina(self, pagina):
        # O vídeo nativo captura a navegação, a digitação, os cliques e as respostas.
        inicio = time.monotonic()
        caminho = pagina.video.path()
        self.paginas[pagina] = {"inicio": inicio, "ultimo": 0.0, "video": str(caminho)}
        return pagina

    def tela(self, pagina, titulo, legenda, caminho, busca, mobile=False, duracao=12):
        self.atual = pagina
        registro = self.paginas[pagina]
        observado = time.monotonic() - registro["inicio"] - registro["ultimo"]
        # A interação é gravada antes da pausa curta para ler o resultado.
        minimo = max(7.0, min(11.0, len(legenda.split()) / 3.8))
        pagina.wait_for_timeout(max(1600, (minimo - observado) * 1000))
        fim = time.monotonic() - registro["inicio"]
        im, d = self.base(titulo, legenda)
        if mobile:
            d.text(
                (570, 150), "Cliente Flutter", fill=TEAL, font=self.font(30, bold=True)
            )
            d.text((570, 198), "Tela de celular", fill=MUTED, font=self.font(23))
            linha = self.trecho(
                im, d, caminho, busca, xy=(570, 255), largura=1230, linhas=18, size=23
            )
            x, y, w, h = 80, 140, 373, 710
        else:
            linha = self.trecho(im, d, caminho, busca)
            x, y, w, h = 45, 140, 1260, 689
        numero = len(self.cenas) + 1
        painel = f"paineis/{numero:03d}.png"
        im.save(self.saida / painel)
        self.cenas.append(
            {
                "titulo": titulo,
                "legenda": legenda,
                "sprint": self.sprint,
                "codigo": f"{caminho}:{linha}",
                "painel": painel,
                "origem": registro["video"],
                "inicioOrigem": registro["ultimo"],
                "duracaoOrigem": fim - registro["ultimo"],
                "area": [x, y, w, h],
            }
        )
        registro["ultimo"] = fim
        (self.saida / "cenas.json").write_text(
            json.dumps(self.cenas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Fluxo {numero:02d}: Sprint {self.sprint} — {titulo}", flush=True)

    def dados(self, titulo, dados, legenda, caminho, busca, duracao=14):
        # Mantém o sistema visível: consultas e navegação acompanham a explicação.
        pagina = self.atual
        if pagina is None or pagina.is_closed():
            return
        mobile = pagina.viewport_size["width"] < 600
        if mobile:
            mobile_operacao(pagina, "Consultar saldo")
            pagina.get_by_role("button", name="Consultar saldo", exact=True).click()
            pagina.wait_for_timeout(600)
            pagina.mouse.wheel(0, 180)
            pagina.wait_for_timeout(500)
            pagina.mouse.wheel(0, -180)
        elif ":15672" in pagina.url:
            pagina.reload()
            pagina.wait_for_timeout(750)
            pagina.mouse.move(450, 440)
            pagina.mouse.wheel(0, 180)
            pagina.wait_for_timeout(500)
            pagina.mouse.wheel(0, -180)
        else:
            if (
                isinstance(dados, dict)
                and dados.get("metodo") == "POST"
                and dados.get("caminho") == "/contas"
                and dados.get("http") == 400
            ):
                pagina.locator("summary").click()
                for campo in ("id", "nomeAluno", "saldoInicial"):
                    web_preencher(
                        pagina,
                        f"#criar-form [name={campo}]",
                        str(dados["pedido"][campo]),
                    )
                with pagina.expect_response(
                    lambda r: r.request.method == "POST" and r.url.endswith("/contas")
                ):
                    pagina.locator("#criar-form button").click()
                pagina.locator("summary").click()
                pagina.locator("#mensagem").scroll_into_view_if_needed()
                self.tela(pagina, titulo, legenda, caminho, busca)
                return
            if isinstance(dados, dict) and dados.get("metodo") == "GET":
                conta = re.match(r"/contas/(\d+)", dados.get("caminho", ""))
                if conta:
                    consultar_web(pagina, int(conta.group(1)))
            else:
                pagina.locator("#consulta-form button").click()
            pagina.wait_for_timeout(500)
            if pagina.locator("#banco-panel").is_visible() and not (
                isinstance(dados, dict) and dados.get("http", 200) >= 400
            ):
                pagina.locator("#historico-atualizar").click()
                pagina.wait_for_timeout(500)
                pagina.locator(".history").scroll_into_view_if_needed()
                pagina.wait_for_timeout(500)
                pagina.locator("#consulta-form").scroll_into_view_if_needed()
        self.tela(pagina, titulo, legenda, caminho, busca, mobile=mobile)

    def exportar(self):
        indice = [
            "# ICEIBank — fluxos das três sprints",
            "",
            "Navegação, digitação, cliques e resultados gravados no navegador, com código ao lado e legendas.",
            "Cliente mobile executado em Flutter Web, em tela de celular.",
            "",
            "| Início | Sprint | Fluxo | Código |",
            "| --- | --- | --- | --- |",
        ]
        srt = []
        tempo = 0.0
        arquivos = []

        def marca(segundos, srt=False):
            milis = round(segundos * 1000)
            h = milis // 3600000
            m = milis % 3600000 // 60000
            s = milis % 60000 // 1000
            ms = milis % 1000
            return f"{h:02}:{m:02}:{s:02}" + (f",{ms:03}" if srt else "")

        for n, c in enumerate(self.cenas, 1):
            # Os fluxos são apresentados em velocidade normal, a 15 quadros/s.
            frames = round(c["duracaoOrigem"] * 15)
            duracao = frames / 15
            c["duracao"] = duracao
            x, y, w, h = c["area"]
            saida = self.saida / f"clipes/{n:03d}.mp4"
            filtro = (
                f"[0:v]scale={w}:{h}:flags=lanczos,fps=15,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=1[v];"
                f"[1:v]format=rgb24[p];[p][v]overlay={x}:{y}:shortest=1,format=yuv420p[out]"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    str(c["inicioOrigem"]),
                    "-i",
                    c["origem"],
                    "-loop",
                    "1",
                    "-framerate",
                    "15",
                    "-i",
                    str(self.saida / c["painel"]),
                    "-filter_complex_threads",
                    "1",
                    "-filter_complex",
                    filtro,
                    "-map",
                    "[out]",
                    "-frames:v",
                    str(frames),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "22",
                    "-threads",
                    "2",
                    "-an",
                    "-movflags",
                    "+faststart",
                    str(saida),
                ],
                check=True,
            )
            arquivos.append(saida)
            indice.append(
                f"| {marca(tempo)} | {c['sprint']} | {c['titulo']} | `{c['codigo']}` |"
            )
            srt.append(
                f"{n}\n{marca(tempo, True)} --> {marca(tempo + duracao, True)}\nSprint {c['sprint']} — {c['titulo']}\n{c['legenda']}\n"
            )
            tempo += duracao
            print(f"Composição {n}/{len(self.cenas)}", flush=True)
        lista = self.saida / "concat.txt"
        lista.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in arquivos), encoding="utf-8"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lista),
                "-c",
                "copy",
                "-an",
                "-movflags",
                "+faststart",
                str(self.saida / "ICEIBank-3-sprints.mp4"),
            ],
            check=True,
        )
        (self.saida / "ICEIBank-roteiro.md").write_text(
            "\n".join(indice) + "\n", encoding="utf-8"
        )
        (self.saida / "ICEIBank-legendas.srt").write_text(
            "\n".join(srt), encoding="utf-8"
        )
        (self.saida / "cenas.json").write_text(
            json.dumps(self.cenas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Vídeo pronto: {tempo:.2f} segundos | {len(self.cenas)} fluxos", flush=True
        )


CURSOR = """() => {
  document.addEventListener('DOMContentLoaded', () => {
    const p=document.createElement('div');p.id='cursor-apresentacao';
    Object.assign(p.style,{position:'fixed',width:'17px',height:'17px',border:'2px solid #102a43',
      borderRadius:'50%',background:'#55ddc099',pointerEvents:'none',zIndex:'2147483647',
      left:'-30px',top:'-30px',transition:'transform .12s'});document.body.appendChild(p);
    document.addEventListener('pointermove',e=>{p.style.left=(e.clientX-8)+'px';p.style.top=(e.clientY-8)+'px'},true);
    document.addEventListener('pointerdown',()=>{p.style.transform='scale(1.65)';setTimeout(()=>p.style.transform='',230)},true);
  });
}"""


class ContextoGravado:
    def __init__(self, contexto, filme):
        self.contexto, self.filme = contexto, filme

    def new_page(self):
        return self.filme.registrar_pagina(self.contexto.new_page())

    def __getattr__(self, nome):
        return getattr(self.contexto, nome)


class NavegadorGravado:
    def __init__(self, browser, filme):
        self.browser, self.filme = browser, filme

    def new_context(self, **opcoes):
        viewport = opcoes.get("viewport", {"width": 1280, "height": 700})
        contexto = self.browser.new_context(
            **opcoes,
            record_video_dir=str(self.filme.saida / "originais"),
            record_video_size=viewport,
        )
        contexto.add_init_script(CURSOR)
        return ContextoGravado(contexto, self.filme)

    def new_page(self, **opcoes):
        return self.new_context(**opcoes).new_page()

    def close(self):
        for contexto in list(self.browser.contexts):
            contexto.close()
        self.browser.close()

    def __getattr__(self, nome):
        return getattr(self.browser, nome)


def web_preencher(pagina, seletor, valor):
    campo = pagina.locator(seletor)
    campo.click()
    pagina.wait_for_timeout(180)
    campo.press("ControlOrMeta+A")
    campo.press_sequentially(valor, delay=75)
    pagina.wait_for_timeout(180)


def entrar_web(p):
    p.goto("http://localhost:4078")
    web_preencher(p, "[name=usuario]", "aluno")
    web_preencher(p, "[name=senha]", "iceibank-sprint1")
    p.locator("#login-form button").click()
    p.locator("#banco-panel").wait_for(state="visible")


def consultar_web(p, id):
    p.locator("#agencia").select_option(str(id % 3))
    web_preencher(p, "#conta", str(id))
    with p.expect_response(
        lambda r: (
            f"/contas/{id}" in r.url
            and r.request.method == "GET"
            and "/historico" not in r.url
        )
    ):
        p.locator("#consulta-form button").click()


def operar_web(p, tipo, valor, destino=None):
    p.locator("#operacao").select_option(tipo)
    if destino is not None:
        web_preencher(p, "#operacao-form [name=destino]", str(destino))
    web_preencher(p, "#operacao-form [name=valor]", valor)
    with p.expect_response(
        lambda r: (
            r.request.method == "POST"
            and ("/contas/" in r.url or "/transferencias" in r.url)
        )
    ) as resultado:
        p.locator("#confirmar").click()
    p.wait_for_timeout(250)
    return {"http": resultado.value.status, "resposta": resultado.value.json()}


def sprint1(f, browser, codigo):
    f.sprint, f.codigo = 1, codigo
    with Cluster(1, codigo, f.saida / "execucao/sprint1") as c:
        page = browser.new_page(viewport={"width": 1280, "height": 700}, locale="pt-BR")
        page.goto("http://localhost:4078")
        entrar_web(page)
        f.tela(
            page,
            "Acesso web · login do operador",
            "O frontend envia usuário e senha a POST /auth/login. O backend valida o hash Argon2 e emite JWT temporário.",
            "agencia/app/auth.py",
            "def login",
        )
        for id, nome in [(1, "Carla"), (2, "Diego"), (3, "Bruno")]:
            c.criar(id, nome)
        page.locator("summary").click()
        web_preencher(page, "#criar-form [name=id]", "0")
        web_preencher(page, "#criar-form [name=nomeAluno]", "Ana")
        web_preencher(page, "#criar-form [name=saldoInicial]", "100.00")
        with page.expect_response(
            lambda r: r.url.endswith("/contas") and r.request.method == "POST"
        ) as resposta:
            page.locator("#criar-form button").click()
        assert resposta.value.status == 201
        page.locator("summary").click()
        consultar_web(page, 0)
        f.tela(
            page,
            "Criar conta e consultar saldo",
            "Conta 0 criada pela interface com R$ 100,00. A conta pertence à Agência 0; contas 1 e 2 pertencem às agências 1 e 2.",
            "agencia/app/controllers/contas_controller.py",
            "async def criar_conta",
        )
        falha = c.api(
            "POST",
            0,
            "/contas",
            {"id": 4, "nomeAluno": "Agência incorreta", "saldoInicial": "1.00"},
            400,
        )
        f.dados(
            "Particionamento validado pelo servidor",
            falha,
            "Criar a conta 4 na Agência 0 retorna HTTP 400: 4 % 3 = 1. A regra está no backend e não depende da interface.",
            "agencia/app/config.py",
            "def agencia_responsavel",
        )
        dep = operar_web(page, "depositar", "25.00")
        assert dep["http"] == 200
        assert c.saldo(0) == "125.00"
        f.tela(
            page,
            "Depósito · R$ 100,00 → R$ 125,00",
            "O depósito de R$ 25,00 altera o saldo em Decimal, avança o relógio e registra o evento. A interface consulta o resultado atualizado.",
            "agencia/app/controllers/contas_controller.py",
            "async def depositar",
        )
        saque = operar_web(page, "sacar", "10.00")
        assert saque["http"] == 200
        assert c.saldo(0) == "115.00"
        f.tela(
            page,
            "Saque · R$ 125,00 → R$ 115,00",
            "O saque de R$ 10,00 exige saldo suficiente. O lock da agência protege a operação e os logs guardam o saldo após a movimentação.",
            "agencia/app/controllers/contas_controller.py",
            "async def sacar",
        )
        local = operar_web(page, "transferir", "15.00", 3)
        assert local["http"] == 200
        assert c.saldo(0) == "100.00" and c.saldo(3) == "115.00"
        f.tela(
            page,
            "Transferência local · conta 0 → conta 3",
            "R$ 15,00 entre contas da Agência 0: origem R$ 100,00, destino R$ 115,00. Débito e crédito ocorrem no mesmo processo.",
            "agencia/app/controllers/transferencias_controller.py",
            "if agencia_destino == estado.agencia_id",
        )
        remota = operar_web(page, "remota", "30.00", 1)
        assert remota["http"] == 200
        assert c.saldo(0) == "70.00" and c.saldo(1) == "130.00"
        f.tela(
            page,
            "Transferência HTTP · conta 0 → conta 1",
            "A origem envia crédito HTTP autenticado à Agência 1 e aguarda a resposta. R$ 30,00: origem R$ 70,00 e destino R$ 130,00.",
            "agencia/app/controllers/transferencias_controller.py",
            "timestamp_envio =",
        )
        consultar_web(page, 1)
        f.tela(
            page,
            "Conferência na agência de destino",
            "A consulta à Agência 1 confirma os R$ 130,00. O JWT interno entre agências usa chave e audiência distintas do token do operador.",
            "agencia/app/controllers/contas_controller.py",
            "async def consultar_conta",
        )
        consultar_web(page, 0)
        erro = operar_web(page, "sacar", "9999.00")
        assert erro["http"] == 400
        f.tela(
            page,
            "Erro visível · saldo insuficiente",
            "Saque acima do saldo retorna HTTP 400 e a interface exibe a mensagem. O saldo continua em R$ 70,00.",
            "agencia/frontend/app.js",
            "async function",
        )
        semjwt = c.cliente.get(
            "http://127.0.0.1:4078/contas/0", headers={"Authorization": ""}
        )
        assert semjwt.status_code == 401
        negativo = c.api("POST", 0, "/contas/0/depositar", {"valor": "-1.00"}, 422)
        f.dados(
            "JWT e validação de entradas",
            {
                "sem_token": {"http": 401, "resposta": semjwt.json()},
                "valor_negativo": negativo,
            },
            "Sem JWT: HTTP 401. Valor negativo: HTTP 422. As duas requisições são recusadas antes de movimentar o saldo.",
            "agencia/app/auth.py",
            "def usuario_autenticado",
        )
        page.locator("#historico-atualizar").click()
        page.locator("#historico-tabela").wait_for(state="visible")
        page.locator(".history").scroll_into_view_if_needed()
        f.tela(
            page,
            "Adicional · histórico por conta",
            "O histórico consulta GET /contas/0/historico. Mostra transações, valores e saldo após cada evento, com paginação por offset e limite.",
            "agencia/app/controllers/contas_controller.py",
            "async def consultar_historico",
        )
        pag = c.api("GET", 0, "/contas/0/historico?offset=2&limite=2")
        f.dados(
            "Paginação do histórico",
            pag,
            "A consulta com offset=2 e limite=2 retorna um recorte do histórico real. O estado consultável pertence ao processo atual.",
            "agencia/app/services/registro_eventos.py",
            "def historico",
        )
        programa = (
            "from pathlib import Path; from agencia.mesclar_logs import carregar_eventos,imprimir_linha_do_tempo; "
            f"imprimir_linha_do_tempo(carregar_eventos(Path({str(c.dados)!r})))"
        )
        saida = subprocess.check_output(
            [__import__("sys").executable, "-c", programa],
            cwd=codigo,
            env=c.env,
            text=True,
        )
        (c.dados / "linha-do-tempo.txt").write_text(saida, encoding="utf-8")
        recorte = "\n".join(
            l for l in saida.splitlines() if "CRIAR_CONTA" in l or "TRANSFERENCIA_" in l
        )
        f.dados(
            "Linha do tempo · logs das três agências",
            recorte,
            "Os logs reais mostram as criações independentes e a transferência. O timestamp do recebimento é maior que o do envio; empates isolados não provam concorrência.",
            "agencia/mesclar_logs.py",
            "def carregar_eventos",
        )
        c.parar(1)
        consultar_web(page, 0)
        falha = operar_web(page, "remota", "10.00", 1)
        assert falha["http"] == 502
        assert c.saldo(0) == "60.00"
        f.dados(
            "Falha remota HTTP · débito permanece",
            falha,
            "Com a Agência 1 desligada, o pedido retorna HTTP 502. A origem cai de R$ 70,00 para R$ 60,00: esta versão ainda não compensa o débito remoto.",
            "agencia/app/controllers/transferencias_controller.py",
            "def _erro_falha_remota",
        )
        c.iniciar(1)
        falta = c.api("GET", 1, "/contas/1", esperado=404)
        f.dados(
            "Reinício · contas não persistidas",
            falta,
            "Após reiniciar a Agência 1, a conta 1 retorna HTTP 404. Os arquivos de log permanecem, mas as contas e os saldos estão em memória.",
            "agencia/app/estado_agencia.py",
            "class EstadoAgencia",
        )
        c.parar(2)
        c.env["JWT_TTL_SECONDS"] = "1"
        c.iniciar(2)
        token = c.cliente.post(
            "http://127.0.0.1:4080/auth/login",
            json={"usuario": "aluno", "senha": "iceibank-sprint1"},
        ).json()["access_token"]
        time.sleep(2)
        exp = c.cliente.get(
            "http://127.0.0.1:4080/contas/2",
            headers={"Authorization": "Bearer " + token},
        )
        assert exp.status_code == 401
        page.evaluate("t => { token = t; }", token)
        f.dados(
            "Sessão expirada · JWT recusado",
            {
                "validadeConfigurada": "1 segundo",
                "esperaReal": "2 segundos",
                "http": exp.status_code,
                "resposta": exp.json(),
            },
            "A Agência 2 foi iniciada com JWT de 1 segundo. Após esperar 2 segundos, a consulta retorna HTTP 401 por expiração, antes de acessar a conta.",
            "agencia/app/auth.py",
            "def validar_token",
        )
        page.close()


def sprint2(f, browser, codigo):
    f.sprint, f.codigo = 2, codigo
    with Cluster(2, codigo, f.saida / "execucao/sprint2") as c:
        c.criar(0, "Ana")
        c.criar(1, "Carla")
        page = browser.new_page(viewport={"width": 1280, "height": 700}, locale="pt-BR")
        entrar_web(page)
        consultar_web(page, 0)
        r = operar_web(page, "remota", "15.00", 1)
        assert r["http"] == 200 and r["resposta"]["status"] == "publicada"
        esperar(lambda: c.saldo(1) == "115.00")
        f.tela(
            page,
            "Publicar transferência assíncrona",
            "R$ 15,00 saem da conta 0. A resposta publicada confirma o RabbitMQ; o crédito da conta 1 é feito pelo consumidor da Agência 1.",
            "agencia/app/controllers/transferencias_controller.py",
            "await request.app.state.mensageria.publicar",
        )
        f.dados(
            "Resposta de publicação e crédito confirmado",
            {
                "POST /transferencias": r,
                "consultaOrigem": c.saldo(0),
                "consultaDestino": c.saldo(1),
            },
            "A resposta contém idTransferencia e vetorEnvio. Consultas posteriores confirmam origem R$ 85,00 e destino R$ 115,00.",
            "agencia/app/services/creditos.py",
            "async def processar_credito",
        )
        manager = browser.new_page(viewport={"width": 1280, "height": 700})
        manager.goto("http://127.0.0.1:15672")
        web_preencher(manager, "[name=username]", "guest")
        web_preencher(manager, "[name=password]", "guest")
        manager.locator("input[type=submit]").click()
        manager.wait_for_timeout(1000)
        manager.goto("http://127.0.0.1:15672/#/queues")
        manager.wait_for_timeout(1000)
        f.tela(
            manager,
            "RabbitMQ Manager · filas reais",
            "O Manager mostra as filas por agência no vhost isolado deste ensaio. Cada fila tem binding agencia.N.creditar no exchange iceibank.eventos.",
            "agencia/app/services/mensageria.py",
            "async def iniciar",
        )
        filas = c.gerencia.get("/api/queues/" + c.vhost).json()
        top = [
            {
                "fila": q["name"],
                "duravel": q["durable"],
                "consumidores": q.get("consumers"),
                "argumentos": q["arguments"],
            }
            for q in filas
        ]
        f.dados(
            "Topologia AMQP · filas duráveis",
            json.dumps(top[:3], ensure_ascii=False, indent=2),
            "Filas duráveis e mensagens persistentes preservam a mensagem no broker. Isso não transforma as contas em memória em contas persistentes.",
            "agencia/app/services/mensageria.py",
            "declare_queue",
        )
        eventos = []
        for arquivo in c.dados.glob("eventos-agencia-*.jsonl"):
            eventos += [json.loads(l) for l in arquivo.read_text().splitlines()]
        cria = [e for e in eventos if e["tipo"] == "CRIAR_CONTA"]
        deb = next(e for e in eventos if e["tipo"] == "TRANSFERENCIA_DEBITO")
        cred = next(e for e in eventos if e["tipo"] == "TRANSFERENCIA_CREDITO_REMOTO")
        from agencia.app.services.relogio_vetorial import comparar_vetores

        assert (
            comparar_vetores(cria[0]["timestampVetorial"], cria[1]["timestampVetorial"])
            == "CONCORRENTES"
        )
        assert (
            comparar_vetores(deb["timestampVetorial"], cred["timestampVetorial"])
            == "ANTES"
        )
        causal = [
            {
                "tipo": e["tipo"],
                "agencia": e["agencia"],
                "vetor": e["timestampVetorial"],
            }
            for e in [*cria, deb, cred]
        ]
        f.dados(
            "Vetores · concorrência e causalidade",
            causal,
            "Criações independentes: vetores incomparáveis, portanto concorrentes. Débito → crédito remoto: vetor do débito ANTES do vetor do crédito.",
            "agencia/app/services/relogio_vetorial.py",
            "def comparar_vetores",
        )
        c.parar(1)
        ret = c.api(
            "POST",
            0,
            "/transferencias",
            {"idOrigem": 0, "idDestino": 1, "valor": "15.00"},
        )

        def fila_retida():
            q = c.gerencia.get(f"/api/queues/{c.vhost}/fila-agencia-1").json()
            return (
                q if q.get("messages_ready") == 1 and q.get("consumers") == 0 else None
            )

        fila = esperar(fila_retida)
        manager.reload()
        manager.wait_for_timeout(1000)
        f.tela(
            manager,
            "Agência 1 offline · mensagem retida",
            "Com o destino parado, a nova transferência continua publicada. A fila da Agência 1 conserva 1 mensagem e tem 0 consumidores.",
            "agencia/app/services/mensageria.py",
            "async def publicar",
        )
        f.dados(
            "Conferência da fila durante a falha",
            {
                "resposta": ret["resposta"],
                "fila": {
                    k: fila.get(k) for k in ["name", "messages_ready", "consumers"]
                },
                "saldoOrigem": c.saldo(0),
            },
            "A origem já está em R$ 70,00. O destino ainda não consumiu o segundo crédito. Publicação e aplicação são etapas distintas.",
            "agencia/app/controllers/transferencias_controller.py",
            "async def transferir",
        )
        c.iniciar(1)
        falta = c.api("GET", 1, "/contas/1", esperado=404)

        def dlq():
            r = c.gerencia.post(
                f"/api/queues/{c.vhost}/fila-agencia-1.nao-processadas/get",
                json={"count": 1, "ackmode": "ack_requeue_true", "encoding": "auto"},
            )
            return r.json() or None

        mensagens = esperar(dlq)
        msg = mensagens[0]
        assert msg["properties"]["headers"]["x-death"][0]["reason"] == "rejected"
        f.dados(
            "Adicional · crédito rejeitado na DLQ",
            {
                "contaAposReinicio": falta,
                "mensagem": json.loads(msg["payload"]),
                "x-death.reason": "rejected",
                "delivery_mode": msg["properties"]["delivery_mode"],
            },
            "A agência reiniciada perdeu a conta. O crédito é rejeitado e preservado na DLQ; não há recuperação automática do saldo nem compensação da origem.",
            "agencia/app/services/creditos.py",
            "async def processar_credito",
            duracao=18,
        )
        c.criar(1, "Conta recriada", "1.00")
        assert c.saldo(1) == "1.00"
        f.dados(
            "DLQ não reaplica o crédito automaticamente",
            c.api("GET", 1, "/contas/1"),
            "Ao recriar a conta com R$ 1,00, ela continua com R$ 1,00. A mensagem preservada exige tratamento; a DLQ não é um mecanismo de estorno.",
            "agencia/app/services/mensageria.py",
            "async def receber",
        )
        manager.close()
        page.close()


def mobile_habilitar(p):
    p.locator("flt-semantics-placeholder").dispatch_event("click")
    p.wait_for_timeout(700)


def mobile_operacao(p, rotulo):
    p.get_by_role("button", name=re.compile(r"^Operação ")).click()
    p.get_by_role("menuitem", name=rotulo, exact=True).click()
    p.wait_for_timeout(250)


def mobile_preencher(p, nome, valor):
    p.get_by_role("textbox", name=nome, exact=True).click()
    p.wait_for_timeout(350)
    p.keyboard.press("ControlOrMeta+A")
    p.keyboard.type(valor, delay=80)
    p.wait_for_timeout(350)
    p.keyboard.press("Tab")
    p.wait_for_timeout(350)


def mobile_enviar(p, rotulo):
    with p.expect_response(
        lambda r: (
            r.request.method == "POST"
            and ("/contas" in r.url or "/transferencias" in r.url)
        )
    ) as r:
        p.get_by_role("button", name=rotulo, exact=True).click()
    r.value.body()
    p.wait_for_timeout(500)
    assert r.value.status in (200, 201), r.value.text()


def sprint3(f, browser, codigo, flutter_web):
    f.sprint, f.codigo = 3, codigo
    with (
        Cluster(3, codigo, f.saida / "execucao/sprint3") as c,
        servidor_flutter(flutter_web),
    ):
        esperar(lambda: c.lider([0, 1, 2], 2))
        context = browser.new_context(
            viewport={"width": 420, "height": 800},
            locale="pt-BR",
            is_mobile=True,
            has_touch=True,
        )
        p = context.new_page()
        p.goto("http://127.0.0.1:8080")
        p.wait_for_timeout(2500)
        mobile_habilitar(p)
        f.tela(
            p,
            "Painel Flutter · líder e disponibilidade",
            "As três agências respondem e a líder é a Agência 2. O app consulta o cluster a cada dois segundos enquanto está em primeiro plano.",
            "app_mobile/lib/main.dart",
            "Future<void> atualizarCluster",
            mobile=True,
        )
        mobile_preencher(p, "Usuário", "aluno")
        mobile_preencher(p, "Senha", "iceibank-sprint1")
        p.get_by_role("button", name="Entrar", exact=True).click()
        p.get_by_role("textbox", name="Número da conta", exact=True).wait_for()
        f.tela(
            p,
            "Login mobile · mesma API, JWT em memória",
            "O app tenta autenticar pela líder e, se necessário, pelas demais agências. A sessão é temporária; o cache fica separado por servidor e usuário.",
            "app_mobile/lib/api.dart",
            "Future<void> entrar",
            mobile=True,
        )
        mobile_operacao(p, "Criar conta")
        mobile_preencher(p, "Número da conta", "0")
        mobile_preencher(p, "Nome", "Ana Mobile")
        mobile_preencher(p, "Saldo inicial", "100.00")
        mobile_enviar(p, "Criar conta")
        assert c.saldo(0) == "100.00"
        f.tela(
            p,
            "Criar conta pelo cliente Flutter",
            "A conta 0 é criada com R$ 100,00 na Agência 0. O cliente calcula id % 3 e envia POST /contas à agência responsável.",
            "app_mobile/lib/api.dart",
            "Future<Json> criar",
            mobile=True,
        )
        c.criar(1, "Carla Mobile")
        c.criar(3, "Bruno Mobile")
        mobile_operacao(p, "Consultar saldo")
        p.get_by_role("button", name="Consultar saldo", exact=True).click()
        p.wait_for_timeout(600)
        f.tela(
            p,
            "Consultar saldo e guardar estado local",
            "A consulta salva saldo confirmado, vetorAtual e versaoAgencia no Hive. Esse estado é a base das operações offline.",
            "app_mobile/lib/offline.dart",
            "Future<bool> consultar",
            mobile=True,
        )
        mobile_operacao(p, "Depositar")
        mobile_preencher(p, "Valor", "25.00")
        mobile_enviar(p, "Depositar")
        assert c.saldo(0) == "125.00"
        f.tela(
            p,
            "Depósito mobile · R$ 125,00 confirmados",
            "O app registra a operação local e sincroniza com POST /contas/0/sincronizar. O servidor confere a versão e o vetor antes de aplicar o depósito.",
            "app_mobile/lib/offline.dart",
            "Future<bool> registrar",
            mobile=True,
        )
        mobile_operacao(p, "Sacar")
        mobile_preencher(p, "Valor", "10.00")
        mobile_enviar(p, "Sacar")
        assert c.saldo(0) == "115.00"
        f.tela(
            p,
            "Saque mobile · R$ 115,00 confirmados",
            "O saque de R$ 10,00 foi aceito pelo servidor. O cliente usa centavos inteiros e o backend usa Decimal para valores monetários.",
            "app_mobile/lib/main.dart",
            "case Operacao.depositar || Operacao.sacar",
            mobile=True,
        )
        mobile_operacao(p, "Transferir")
        mobile_preencher(p, "Conta de destino", "3")
        mobile_preencher(p, "Valor", "15.00")
        mobile_enviar(p, "Transferir")
        assert c.saldo(0) == "100.00" and c.saldo(3) == "115.00"
        f.tela(
            p,
            "Transferência local pelo app",
            "Conta 0 → conta 3, R$ 15,00. A origem fica com R$ 100,00 e o destino com R$ 115,00. Transferências exigem conexão.",
            "app_mobile/lib/api.dart",
            "Future<Json> transferir",
            mobile=True,
        )
        mobile_preencher(p, "Conta de destino", "1")
        mobile_preencher(p, "Valor", "20.00")
        mobile_enviar(p, "Transferir")
        esperar(lambda: c.saldo(1) == "120.00")
        assert c.saldo(0) == "80.00"
        f.tela(
            p,
            "Transferência entre agências pelo app",
            "Conta 0 → conta 1, R$ 20,00. O backend publica no RabbitMQ; consulta ao destino confirma R$ 120,00 e a origem fica com R$ 80,00.",
            "agencia/app/controllers/transferencias_controller.py",
            "await request.app.state.mensageria.publicar",
            mobile=True,
        )
        mobile_operacao(p, "Consultar histórico")
        p.get_by_role("button", name="Consultar histórico", exact=True).click()
        p.wait_for_timeout(600)
        p.mouse.wheel(0, 450)
        p.wait_for_timeout(400)
        f.tela(
            p,
            "Histórico no Flutter",
            "O app consulta a mesma rota de histórico e mostra as movimentações reais da conta. A fila offline possui seus próprios identificadores de operação.",
            "app_mobile/lib/main.dart",
            "case Operacao.historico",
            mobile=True,
        )
        p.mouse.wheel(0, -2000)
        p.wait_for_timeout(300)
        c.parar(2)
        esperar(lambda: c.lider([0, 1], 1))
        p.wait_for_timeout(3200)
        f.tela(
            p,
            "Bully · queda da Agência 2, líder passa a 1",
            "A líder 2 foi encerrada. As agências 0 e 1 elegem a Agência 1, e o painel atualiza automaticamente a disponibilidade.",
            "agencia/app/services/eleicao.py",
            "async def _verificar",
            mobile=True,
            duracao=16,
        )
        c.iniciar(2)
        esperar(lambda: c.lider([0, 1, 2], 2))
        p.wait_for_timeout(2600)
        f.tela(
            p,
            "Bully · retorno da Agência 2",
            "Ao retornar, a Agência 2 reassume por ter o maior ID. Essa eleição não replica contas nem transfere os saldos da agência que caiu.",
            "agencia/app/services/eleicao.py",
            "async def _disputar",
            mobile=True,
            duracao=16,
        )
        # Freeze only this browser context's network. Backend and RabbitMQ remain live.
        mobile_operacao(p, "Consultar saldo")
        p.get_by_role("button", name="Consultar saldo", exact=True).click()
        p.wait_for_timeout(600)
        context.set_offline(True)
        p.wait_for_timeout(3600)
        mobile_operacao(p, "Depositar")
        mobile_preencher(p, "Valor", "20.00")
        p.get_by_role("button", name="Depositar", exact=True).click()
        p.wait_for_timeout(4000)
        assert c.saldo(0) == "80.00"
        f.tela(
            p,
            "Sem rede · depósito fica pendente",
            "A rede deste cliente foi desligada, mantendo os servidores ativos. Depósito de R$ 20,00: saldo confirmado R$ 80,00, provisório R$ 100,00 e item pendente.",
            "app_mobile/lib/offline.dart",
            "Future<void> gravar",
            mobile=True,
            duracao=18,
        )
        context.set_offline(False)
        esperar(lambda: c.saldo(0) == "100.00")
        p.wait_for_timeout(2800)
        f.tela(
            p,
            "Reconexão · sincronização automática",
            "Ao reconectar com o app aberto, a fila é enviada em ordem. O servidor aceita o depósito; o saldo confirmado vira R$ 100,00 e o item sai da fila.",
            "app_mobile/lib/main.dart",
            "Future<void> sincronizarPendentes",
            mobile=True,
            duracao=18,
        )
        # A fresh consult establishes the base for the conflict scenario.
        mobile_operacao(p, "Consultar saldo")
        p.get_by_role("button", name="Consultar saldo", exact=True).click()
        p.wait_for_timeout(600)
        context.set_offline(True)
        p.wait_for_timeout(3500)
        mobile_operacao(p, "Depositar")
        mobile_preencher(p, "Valor", "10.00")
        p.get_by_role("button", name="Depositar", exact=True).click()
        p.wait_for_timeout(3800)
        c.api("POST", 0, "/contas/0/depositar", {"valor": "5.00"})
        f.tela(
            p,
            "Conflito preparado · dois clientes",
            "O app offline tem depósito pendente de R$ 10,00. Outro cliente deposita R$ 5,00 no servidor: o estado conhecido pelo app fica desatualizado.",
            "app_mobile/lib/offline.dart",
            "factory Pendencia.nova",
            mobile=True,
        )
        with p.expect_response(
            lambda r: "/sincronizar" in r.url and r.status == 409, timeout=15000
        ) as conflito:
            context.set_offline(False)
        p.wait_for_timeout(2600)
        assert c.saldo(0) == "105.00"
        f.tela(
            p,
            "HTTP 409 · revisão exigida no app",
            "O servidor rejeita a operação com base antiga. O app mostra saldo confirmado R$ 105,00 e aviso de conflito; os R$ 10,00 recusados não são aplicados.",
            "app_mobile/lib/offline.dart",
            "final motivo = status == 409",
            mobile=True,
            duracao=18,
        )
        f.dados(
            "Conflito · resposta real do servidor",
            {"http": conflito.value.status, "resposta": conflito.value.json()},
            "A resposta inclui vetor conhecido, vetor atual e contaAtual. O backend compara e aplica dentro do mesmo lock para evitar atualização concorrente.",
            "agencia/app/controllers/contas_controller.py",
            "relacao = comparar_vetores",
            duracao=18,
        )
        p.get_by_role("button", name="Dispensar avisos desta conta", exact=True).click()
        p.wait_for_timeout(700)
        f.tela(
            p,
            "Revisar e dispensar o aviso",
            "Dispensar o aviso remove o pedido recusado da fila local. Para efetuar o depósito após revisar, o usuário deve enviar uma nova operação.",
            "app_mobile/lib/offline.dart",
            "Future<void> dispensarFalhas",
            mobile=True,
        )
        # Show duplicate synchronization protection with an actual repeated request.
        base = c.api("GET", 0, "/contas/0")["resposta"]
        pedido = {
            "tipo": "DEPOSITO",
            "valor": "1.00",
            "vetorConhecido": base["vetorAtual"],
            "versaoAgencia": base["versaoAgencia"],
            "operacaoId": str(uuid.uuid4()),
        }
        a = c.api("POST", 0, "/contas/0/sincronizar", pedido)
        b = c.api("POST", 0, "/contas/0/sincronizar", pedido)
        assert a["resposta"] == b["resposta"] and c.saldo(0) == "106.00"
        f.dados(
            "Repetição de operação · valor aplicado uma vez",
            {
                "primeiraResposta": a["resposta"],
                "segundaResposta": b["resposta"],
                "saldoFinal": c.saldo(0),
            },
            "Duas requisições iguais com o mesmo operacaoId retornam o mesmo resultado: R$ 106,00. Essa deduplicação vale enquanto a instância mantém o estado em memória.",
            "agencia/app/controllers/contas_controller.py",
            "anterior = estado.sincronizacoes",
            duracao=18,
        )
        contexto = subprocess.check_output(
            [
                "node",
                str(codigo / "agencia/historico-lideranca.js"),
                "--dados",
                str(c.dados),
            ],
            text=True,
        )
        (c.dados / "historico-lideranca.txt").write_text(contexto, encoding="utf-8")
        f.dados(
            "Linha do tempo de liderança",
            contexto,
            "O script lê os JSONL desta execução e mostra as declarações de liderança, inclusive estados transitórios. Bully converge após a rede estabilizar.",
            "agencia/historico-lideranca.js",
            "const ",
            duracao=16,
        )
        context.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sprint1", type=Path, default=fonte(1))
    p.add_argument("--sprint2", type=Path, default=fonte(2))
    p.add_argument("--flutter-web", type=Path, default=ROOT / "app_mobile/build/web")
    p.add_argument("--chromium", default=None)
    p.add_argument(
        "--saida",
        type=Path,
        default=ROOT
        / ".local/apresentacao"
        / datetime.now(UTC).strftime("video-%Y%m%dT%H%M%S%f"),
    )
    p.add_argument(
        "--somente",
        type=int,
        choices=[1, 2, 3],
        help="Grava apenas uma sprint para ensaio",
    )
    args = p.parse_args()
    for n, path in [(1, args.sprint1), (2, args.sprint2)]:
        if args.somente not in (None, n):
            continue
        atual = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
        from scripts.ambiente_apresentacao import VERSOES

        if atual != VERSOES[n]:
            p.error(f"Versão incorreta para Sprint {n}: {atual}")
    if args.somente in (None, 3) and not (args.flutter_web / "index.html").exists():
        p.error("Compile o Flutter Web com ICEIBANK_HOST=127.0.0.1 primeiro.")
    filme = Filme(args.saida)
    versoes = {
        str(n): subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
        for n, path in [(1, args.sprint1), (2, args.sprint2), (3, ROOT)]
        if path.exists()
    }
    (filme.saida / "versoes.json").write_text(
        json.dumps(
            {
                "gravadoEmUTC": datetime.now(UTC).isoformat(),
                "commits": versoes,
                "cliente": "Flutter Web em viewport de celular 420x800",
                "audio": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with sync_playwright() as pw:
        browser = NavegadorGravado(
            pw.chromium.launch(executable_path=args.chromium, headless=True), filme
        )
        try:
            if args.somente in (None, 1):
                sprint1(filme, browser, args.sprint1.resolve())
            if args.somente in (None, 2):
                sprint2(filme, browser, args.sprint2.resolve())
            if args.somente in (None, 3):
                sprint3(filme, browser, ROOT, args.flutter_web)
        except Exception:
            for n, context in enumerate(browser.contexts):
                for j, page in enumerate(context.pages):
                    page.screenshot(path=str(filme.saida / f"debug-{n}-{j}.png"))
                    (filme.saida / f"debug-{n}-{j}.txt").write_text(
                        page.locator("body").aria_snapshot(), encoding="utf-8"
                    )
            raise
        finally:
            browser.close()
    filme.exportar()


if __name__ == "__main__":
    main()
