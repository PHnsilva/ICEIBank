"""Capturas sem edição do Swagger executando requisições HTTP nas agências reais."""
from pathlib import Path
import time

from playwright.sync_api import expect

from agencia.app.auth import emitir_token

EVIDENCIAS = Path(__file__).resolve().parents[2] / "evidencias" / "sprint2" / "regressao"


def consultar_swagger(page, id, token=None):
    page.goto("http://localhost:4078/docs")
    expect(page.locator(".swagger-ui")).to_be_visible()
    if token:
        page.get_by_role("button", name="Authorize", exact=True).click()
        page.locator(".auth-container input").fill(token)
        page.locator(".dialog-ux").get_by_text("Authorize", exact=True).click()
        page.locator(".dialog-ux").get_by_text("Close", exact=True).click()
    bloco = page.locator("#operations-contas-consultar_conta_contas__id_conta__get")
    bloco.locator(".opblock-summary").click()
    bloco.get_by_role("button", name="Try it out").click()
    bloco.get_by_placeholder("id_conta").fill(str(id))
    bloco.get_by_role("button", name="Execute", exact=True).click()
    expect(bloco.locator(".live-responses-table")).to_be_visible()
    return bloco


def test_evidencias_auth_reais(page, contas, agencias):
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    id, c = contas
    page.set_viewport_size({"width": 1440, "height": 1200})
    bloco = consultar_swagger(page, id)
    expect(bloco.locator(".live-responses-table tbody .response-col_status")).to_contain_text("401")
    expect(bloco.locator(".live-responses-table")).to_contain_text("Token ausente ou inválido")
    bloco.screenshot(path=str(EVIDENCIAS / "auth-sem-token.png"))

    token = c.headers["Authorization"].removeprefix("Bearer ")
    bloco = consultar_swagger(page, id, token)
    expect(bloco.locator(".live-responses-table tbody .response-col_status")).to_contain_text("200")
    expect(bloco.locator(".live-responses-table")).to_contain_text('"saldo": "100.00"')
    bloco.screenshot(path=str(EVIDENCIAS / "auth-com-token.png"))

    # Mesma função de emissão e chave do servidor: token de teste válido por 1s.
    curto = emitir_token(agencias["segredo_teste"], "aluno", "iceibank-api", 1, tipo="usuario")
    time.sleep(2)
    bloco = consultar_swagger(page, id, curto)
    expect(bloco.locator(".live-responses-table tbody .response-col_status")).to_contain_text("401")
    expect(bloco.locator(".live-responses-table")).to_contain_text("Token expirado")
    bloco.screenshot(path=str(EVIDENCIAS / "auth-token-expirado.png"))
