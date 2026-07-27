import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data"

sys.path.append(str(BASE_DIR))
sys.path.append(str(PATH_ROOT / "resources"))

from bot import carregar_usuarios, preencher_portal_rapido, INDEX_HTML
from extracao import extrair_dados, extrair_todos_dados
from documento_email import criar_documento, enviar_email

def executar_orquestracao(modo="unico", row_index=0):
    """
    Executa a orquestração do RPA.
    - modo="unico": Extrai e gera documento apenas para a linha especificada (ex: row_index=0).
    - modo="todos": Extrai e gera documento para TODOS os cadastros do portal.
    """
    print("=" * 65)
    print("🚀 INICIANDO ORQUESTRAÇÃO RPA COMPLETA (HYPERAUTOMATION)")
    print("=" * 65)

    usuarios = carregar_usuarios()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False
        )
        page = context.new_page()

        portal_url = f"file://{INDEX_HTML.resolve()}"
        print(f"\n[Etapa 1] Abrindo Portal Fake: {portal_url}")
        page.goto(portal_url)

        # 1. Carga ultra-rápida no portal
        print("\n[Etapa 1] Executando preenchimento ultra-rápido dos dados no portal...")
        preencher_portal_rapido(page, usuarios, qtd=10)

        # 2. Extração dos dados
        if modo == "todos":
            print("\n[Etapa 2] Extraindo dados de TODOS os cadastros...")
            lista_clientes = extrair_todos_dados(page)
        else:
            print(f"\n[Etapa 2] Extraindo dados do cadastro na linha {row_index}...")
            lista_clientes = [extrair_dados(page, row_index=row_index)]

        context.close()

    # 3. Geração de documentos, envio de e-mail e exclusão automática da ficha
    email_destino = "carvalhosannyer@gmail.com"

    for i, cliente in enumerate(lista_clientes, start=1):
        print(f"\n[Etapa 3 - Cliente {i}/{len(lista_clientes)}] Processando: {cliente.get('Nome')} {cliente.get('Sobrenome')}")
        arquivo_docx = criar_documento(cliente)
        print(f"  📄 Documento Word gerado: {arquivo_docx}")

        print(f"  ✉️ Enviando e-mail para {email_destino}...")
        try:
            enviar_email(email_destino, arquivo_docx, apagar_apos_envio=True)
        except Exception as e:
            print(f"  ⚠️ Falha ao enviar e-mail do cliente {cliente.get('Nome')}: {e}")

    print("\n✅ ORQUESTRAÇÃO FINALIZADA COM SUCESSO!")

if __name__ == "__main__":
    executar_orquestracao(modo="unico", row_index=9)
