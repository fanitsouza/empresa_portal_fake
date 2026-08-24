"""
Processo 1 - Envio de Fichas para Assinatura
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Abrir o Portal Fake e carregar dados dos clientes (ou buscar registro específico).
2. Extrair os dados cadastrais (Nome, CPF, E-mail, Telefone, etc.).
3. Gerar a Ficha de Cadastro preenchida (.docx).
4. Disparar e-mail com a ficha em anexo para o cliente assinar.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"
BROWSER_DATA_DIR = RESOURCES_DIR / "browser_data"
INDEX_HTML = RESOURCES_DIR / "portal_fake" / "index.html"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

import importlib.util

def _carregar_modulo_bot_resources():
    bot_path = RESOURCES_DIR / "bot.py"
    spec = importlib.util.spec_from_file_location("bot_portal_resources", str(bot_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_bot_res = _carregar_modulo_bot_resources()
carregar_usuarios = _bot_res.carregar_usuarios
preencher_portal_rapido = _bot_res.preencher_portal_rapido

from extracao import extrair_dados, extrair_todos_dados
from documento_email import criar_documento, enviar_email

LOGGER = logging.getLogger("PROCESSO_1_ENVIO")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(name)s] %(levelname)s: %(message)s")


def executar_processo_1(
    modo: str = "unico",
    row_index: int = 0,
    qtd_carga: int = 10,
    email_destino: str | None = None,
    headless: bool = False,
) -> List[Dict[str, Any]]:
    """
    Executa o Processo 1 de ponta a ponta:
    - Preenche/extrai do portal fake
    - Gera documento Word de ficha
    - Envia por e-mail para assinatura do cliente
    """
    print("\n" + "=" * 70)
    print("🚀 [PROCESSO 1] INICIANDO ENVIO DE FICHAS PARA ASSINATURA")
    print("=" * 70)

    email_destino_padrao = (
        email_destino
        or os.getenv("EMAIL_CLIENTE_TESTE")
        or os.getenv("EMAIL_REMETENTE")
        or "fani.souza19@gmail.com"
    )

    usuarios = carregar_usuarios()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=headless,
        )
        page = context.new_page()

        portal_url = f"file://{INDEX_HTML.resolve()}"
        print(f"\n[Etapa 1] Abrindo Portal Fake: {portal_url}")
        page.goto(portal_url)

        if qtd_carga > 0:
            print(f"\n[Etapa 1.1] Executando pré-carga de {qtd_carga} registros no portal...")
            preencher_portal_rapido(page, usuarios, qtd=qtd_carga)

        if modo == "todos":
            print("\n[Etapa 2] Extraindo dados de TODOS os cadastros...")
            lista_clientes = extrair_todos_dados(page)
        else:
            print(f"\n[Etapa 2] Extraindo dados do cadastro na linha {row_index}...")
            lista_clientes = [extrair_dados(page, row_index=row_index)]

        context.close()

    enviados: List[Dict[str, Any]] = []

    print("\n[Etapa 3] Gerando Fichas e Disparando E-mails...")
    for i, cliente in enumerate(lista_clientes, start=1):
        nome_completo = f"{cliente.get('Nome', '')} {cliente.get('Sobrenome', '')}".strip()
        print(f"\n  ({i}/{len(lista_clientes)}) Processando Cliente: {nome_completo}")

        arquivo_docx = criar_documento(cliente)
        print(f"  📄 Documento Word gerado: {arquivo_docx}")

        destinatario = cliente.get("E-mail") or email_destino_padrao
        print(f"  ✉️ Enviando e-mail para: {destinatario}")

        try:
            enviar_email(destinatario, arquivo_docx, apagar_apos_envio=False)
            enviados.append({"cliente": cliente, "arquivo": arquivo_docx, "email": destinatario, "sucesso": True})
            print(f"  ✅ Ficha enviada com sucesso para {destinatario}!")
        except Exception as e:
            LOGGER.error(f"Falha ao enviar e-mail para {destinatario}: {e}")
            enviados.append({"cliente": cliente, "arquivo": arquivo_docx, "email": destinatario, "sucesso": False, "erro": str(e)})

    print("\n" + "=" * 70)
    print(f"✅ [PROCESSO 1] FINALIZADO COM SUCESSO! ({len(enviados)} fichas processadas)")
    print("=" * 70 + "\n")

    return enviados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 1 - Envio de Fichas de Cadastro para Assinatura por E-mail"
    )
    parser.add_argument(
        "--modo",
        choices=["unico", "todos"],
        default="unico",
        help="Modo de extração: 'unico' (apenas 1 cliente) ou 'todos' (toda a tabela).",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Índice da linha a ser extraída no modo unico (padrão: 0).",
    )
    parser.add_argument(
        "--qtd-carga",
        type=int,
        default=10,
        help="Quantidade de registros para pré-carregar no portal fake (padrão: 10, use 0 para não recarregar).",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="E-mail de destino customizado para receber a ficha.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o navegador em modo oculto.",
    )

    args = parser.parse_args()
    executar_processo_1(
        modo=args.modo,
        row_index=args.row_index,
        qtd_carga=args.qtd_carga,
        email_destino=args.email,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
