import csv
from pathlib import Path
from playwright.sync_api import sync_playwright

PATH_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = PATH_ROOT / "resources" / "portal_fake" / "index.html"
CSV_PATH = PATH_ROOT / "resources" / "cadastros_portal_fake_20.csv"
BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data"

def carregar_usuarios(csv_path=CSV_PATH):
    usuarios = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            usuarios.append(row)
    return usuarios

def preencher_portal_rapido(page, usuarios, qtd=10):
    """
    Preenche o Portal Fake de forma ultra-rápida utilizando o Playwright.
    """
    # Trata diálogos nativos (como o confirm do #btnClearAll)
    page.on("dialog", lambda dialog: dialog.accept())

    # Zerar a base antes de preencher
    page.click("#btnClearAll")

    lista = usuarios[:qtd] if qtd else usuarios
    total = len(lista)
    print(f"[RPA Preenchimento] Cadastrando {total} usuários no Portal Fake...")

    for i, usuario in enumerate(lista, start=1):
        page.click("#btnNovo")
        page.fill("#f_nome", usuario.get("nome", ""))
        page.fill("#f_sobrenome", usuario.get("sobrenome", ""))
        page.fill("#f_cpf", usuario.get("cpf", ""))
        page.fill("#f_email", usuario.get("email", ""))
        page.fill("#f_telefone", usuario.get("telefone", ""))
        page.fill("#f_nascimento", usuario.get("nascimento", ""))
        page.fill("#f_endereco", usuario.get("endereco", ""))
        page.fill("#f_observacao", usuario.get("observacao", ""))

        status = (usuario.get("status") or "ATIVO").upper()
        page.select_option("#f_status", status)

        page.click("#btnSalvar")

    print(f"[RPA Preenchimento] Sucesso! {total} cadastros inseridos no portal.")

def main():
    usuarios = carregar_usuarios()
    with sync_playwright() as p:
        # Usa contexto persistente para salvar localStorage no disco
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False
        )
        page = context.new_page()
        page.goto(f"file://{INDEX_HTML.resolve()}")
        preencher_portal_rapido(page, usuarios, qtd=10)
        context.close()

if __name__ == "__main__":
    main()
