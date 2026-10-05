import pytest
from playwright.sync_api import sync_playwright

from scripts.ambiente_sprint2 import AmbienteSprint2


@pytest.fixture(scope="session")
def agencias(tmp_path_factory):
    with AmbienteSprint2(tmp_path_factory.mktemp("agencias-sprint2")) as ambiente:
        yield {"segredo_teste": ambiente.env["JWT_SECRET"], "dados": ambiente.dados, "ambiente": ambiente}


@pytest.fixture(scope="session")
def navegador(agencias):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(navegador):
    context = navegador.new_context(viewport={"width": 1365, "height": 1080}, locale="pt-BR")
    yield context.new_page()
    context.close()


@pytest.fixture
def contas(request, agencias):
    base = (list(request.session.items).index(request.node) + 1) * 30
    ambiente = agencias["ambiente"]
    for id in (base, base+1, base+2, base+3):
        ambiente.criar(id)
    yield base, ambiente.cliente
