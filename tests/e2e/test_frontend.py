from pathlib import Path
import re

from playwright.sync_api import expect

EVIDENCIAS = Path(__file__).resolve().parents[2] / "evidencias" / "sprint1"


def captura(page, nome):
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCIAS / nome), full_page=True)


def entrar(page):
    page.goto("http://localhost:4078")
    expect(page.locator("#agencia")).to_be_enabled()
    page.get_by_label("Usuário", exact=True).fill("aluno")
    page.get_by_label("Senha", exact=True).fill("senha-e2e")
    page.get_by_role("button", name="Entrar").click()
    expect(page.locator("#banco-panel")).to_be_visible()


def consultar(page, id):
    page.locator("#conta").fill(str(id))
    page.get_by_role("button", name="Consultar saldo").click()
    expect(page.locator("#titular")).to_contain_text(f"Conta {id}")


def operar(page, operacao, valor, destino=None):
    page.locator("#operacao").select_option(operacao)
    if destino is not None: page.get_by_label("Conta de destino", exact=True).fill(str(destino))
    page.get_by_label("Valor (R$)", exact=True).fill(valor)
    page.get_by_role("button", name="Confirmar operação").click()


def test_login_e_erro_de_credenciais(page):
    page.goto("http://localhost:4078")
    expect(page.locator("#agencia")).to_be_enabled()
    captura(page, "frontend-login.png")
    page.get_by_label("Usuário", exact=True).fill("aluno")
    page.get_by_label("Senha", exact=True).fill("errada")
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_role("alert")).to_contain_text("HTTP 401")
    expect(page.locator("#login-panel")).to_be_visible()


def test_fluxo_completo_tres_agencias(page, contas):
    id, c = contas
    erros_js = []
    page.on("pageerror", lambda erro: erros_js.append(str(erro)))
    entrar(page)
    consultar(page, id)
    expect(page.locator("#saldo")).to_contain_text("100,00")
    operar(page, "depositar", "25.00")
    expect(page.locator("#mensagem")).to_contain_text("Depósito realizado")
    operar(page, "sacar", "10.00")
    expect(page.locator("#saldo")).to_contain_text("115,00")
    operar(page, "transferir", "15.00", id+3)
    expect(page.locator("#mensagem")).to_contain_text("Transferência local realizada")
    operar(page, "remota", "20.00", id+1)
    expect(page.locator("#mensagem")).to_contain_text("Transferência entre agências realizada")
    expect(page.locator("#saldo")).to_contain_text("80,00")
    captura(page, "frontend-transferencia.png")
    page.locator("#agencia").select_option("1")
    expect(page.locator("#saldo")).to_have_text("—")
    consultar(page, id+1)
    expect(page.locator("#saldo")).to_contain_text("120,00")
    operar(page, "remota", "10.00", id+2)
    expect(page.locator("#mensagem")).to_contain_text("Transferência entre agências realizada")
    page.locator("#agencia").select_option("2")
    consultar(page, id+2)
    expect(page.locator("#saldo")).to_contain_text("110,00")
    operar(page, "remota", "5.00", id)
    expect(page.locator("#mensagem")).to_contain_text("Transferência entre agências realizada")
    assert [c.get(f"http://localhost:{4078+n%3}/contas/{n}").json()["saldo"] for n in (id, id+1, id+2, id+3)] == ["85.00", "110.00", "105.00", "115.00"]
    page.get_by_role("button", name="Sair da conta").click()
    expect(page.locator("#login-panel")).to_be_visible()
    assert not erros_js


def test_erros_visiveis_e_saldo_preservado(page, contas):
    id, c = contas
    entrar(page)
    consultar(page, id)
    operar(page, "sacar", "999999.00")
    expect(page.get_by_role("alert")).to_contain_text("HTTP 400 — Saldo insuficiente")
    expect(page.locator("#saldo")).to_contain_text("100,00")
    captura(page, "frontend-erro.png")
    page.locator("#conta").fill("999999")
    page.get_by_role("button", name="Consultar saldo").click()
    expect(page.get_by_role("alert")).to_contain_text("HTTP 404")
    expect(page.locator("#saldo")).to_have_text("—")
    consultar(page, id)
    page.route("**/contas/*/depositar", lambda route: route.abort())
    operar(page, "depositar", "1.00")
    expect(page.get_by_role("alert")).to_contain_text("Não foi possível comunicar")
    assert c.get(f"http://localhost:4078/contas/{id}").json()["saldo"] == "100.00"


def test_401_limpa_sessao_e_mobile(page, contas):
    id, _ = contas
    page.set_viewport_size({"width": 390, "height": 844})
    entrar(page)
    consultar(page, id)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.route(f"**/contas/{id}", lambda route: route.fulfill(status=401, json={"detail": "Token expirado. Faça login novamente."}))
    page.get_by_role("button", name="Consultar saldo").click()
    expect(page.get_by_role("alert")).to_contain_text("HTTP 401")
    expect(page.locator("#login-panel")).to_be_visible()
    expect(page.locator("#saldo")).to_have_text("—")


def test_abertura_conta_e_erro_de_agencia(page, contas):
    id, _ = contas
    entrar(page)
    page.get_by_text("Abrir conta de demonstração").click()
    page.get_by_label("Número da nova conta").fill(str(id+6))
    page.get_by_label("Nome do titular").fill("<img src=x onerror=alert(1)>")
    page.get_by_label("Saldo inicial (R$)").fill("12.50")
    page.get_by_role("button", name="Criar conta", exact=True).click()
    expect(page.locator("#mensagem")).to_contain_text("criada com sucesso")
    expect(page.locator("#titular")).to_contain_text("<img src=x")
    assert page.locator("#titular img").count() == 0
    operar(page, "transferir", "1.00", id+1)
    expect(page.get_by_role("alert")).to_contain_text("tipo de transferência")
