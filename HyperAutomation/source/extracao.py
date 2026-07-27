from playwright.sync_api import sync_playwright
from pathlib import Path

PATH_ROOT = Path(__file__).resolve().parent.parent
PORTAL_PATH = PATH_ROOT / "resources" / "portal_fake" / "index.html"
BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data"

def extrair_dados(page=None, row_index=0, cpf=None):
    """
    Extrai dados de um cadastro no Portal Fake.
    - Se 'cpf' for especificado, busca pelo CPF.
    - Caso contrário, extrai a linha especificada por 'row_index' (padrão 0 = primeiro da lista).
    """
    close_browser_after = False

    if page is None:
        p = sync_playwright().start()
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False
        )
        page = context.new_page()
        portal_url = f"file://{PORTAL_PATH.resolve()}"
        page.goto(portal_url)
        close_browser_after = True

    page.wait_for_selector("#tbody", timeout=5000)
    page.wait_for_timeout(500)

    # Se um CPF específico foi solicitado, faz a busca
    if cpf:
        page.fill("#q", cpf)
        page.click("#btnBuscar")
        page.wait_for_timeout(300)

    botoes_editar = page.locator("button[data-action='editar']")
    qtd_registros = botoes_editar.count()

    if qtd_registros > 0:
        idx = min(row_index, qtd_registros - 1)
        botoes_editar.nth(idx).click()
        page.wait_for_selector("#modal:not([hidden])", timeout=3000)

        dados = {
            "Nome": page.locator("#f_nome").input_value(),
            "Sobrenome": page.locator("#f_sobrenome").input_value(),
            "CPF": page.locator("#f_cpf").input_value(),
            "E-mail": page.locator("#f_email").input_value(),
            "Telefone": page.locator("#f_telefone").input_value(),
            "Nascimento": page.locator("#f_nascimento").input_value(),
            "Endereco": page.locator("#f_endereco").input_value()
        }

        page.click("#btnModalClose")
    else:
        print("⚠️ Nenhum registro encontrado para extração.")
        dados = {}

    print(f"\n[Extração] Dados extraídos do registro (linha {row_index}):")
    for campo, valor in dados.items():
        print(f"  • {campo}: {valor}")

    if close_browser_after:
        context.close()
        p.stop()

    return dados

def extrair_todos_dados(page):
    """
    Extrai uma lista contendo os dados de TODOS os cadastros presentes na tabela do Portal Fake.
    """
    page.wait_for_selector("#tbody", timeout=5000)
    botoes_editar = page.locator("button[data-action='editar']")
    total = botoes_editar.count()

    todos = []
    print(f"\n[Extração] Extraindo um total de {total} registros da tabela...")

    for i in range(total):
        botoes_editar = page.locator("button[data-action='editar']")
        botoes_editar.nth(i).click()
        page.wait_for_selector("#modal:not([hidden])", timeout=3000)

        dados = {
            "Nome": page.locator("#f_nome").input_value(),
            "Sobrenome": page.locator("#f_sobrenome").input_value(),
            "CPF": page.locator("#f_cpf").input_value(),
            "E-mail": page.locator("#f_email").input_value(),
            "Telefone": page.locator("#f_telefone").input_value(),
            "Nascimento": page.locator("#f_nascimento").input_value(),
            "Endereco": page.locator("#f_endereco").input_value()
        }
        todos.append(dados)
        page.click("#btnModalClose")

    return todos

if __name__ == "__main__":
    extrair_dados()
