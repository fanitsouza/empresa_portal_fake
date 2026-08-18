"""
Processo 4 - Cadastro Automatizado no Portal Fake / ERP
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Carregar registros aprovados da Planilha Mestra (.xlsx).
2. Validar e normalizar os campos obrigatórios (CPF 11 dígitos, formato de data, etc.).
3. Executar o cadastro automatizado no Portal Fake via Playwright RPA (ou API/ML se configurado).
4. Capturar evidências visuais (screenshots) e registrar logs detalhados de auditoria.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"

INDEX_HTML = RESOURCES_DIR / "portal_fake" / "index.html"
PLANILHA_PADRAO = RESOURCES_DIR / "planilha_mestra.xlsx"
BROWSER_DATA_DIR = RESOURCES_DIR / "browser_data"
PASTA_SCREENSHOTS = RESOURCES_DIR / "screenshots"
PASTA_LOGS = RESOURCES_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

# Reutiliza as funções robustas de cadastro já criadas no projeto
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "processo 3"))

try:
    from cadastro import (
        carregar_usuarios,
        cadastrar_usuarios_api,
        preencher_portal_rapido,
        salvar_evidencia_cadastros,
        configurar_logs,
    )
except ImportError:
    # Se importação direta falhar, importa do caminho relativo
    import importlib.util
    spec = importlib.util.spec_from_file_location("cadastro", str(BASE_DIR / "processo 3" / "cadastro.py"))
    cadastro_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cadastro_mod)
    carregar_usuarios = cadastro_mod.carregar_usuarios
    cadastrar_usuarios_api = cadastro_mod.cadastrar_usuarios_api
    preencher_portal_rapido = cadastro_mod.preencher_portal_rapido
    salvar_evidencia_cadastros = cadastro_mod.salvar_evidencia_cadastros
    configurar_logs = cadastro_mod.configurar_logs

LOGGER = logging.getLogger("PROCESSO_4_CADASTRO")


def executar_processo_4(
    caminho_planilha: Path | str | None = None,
    quantidade: int = 0,
    modo: str = "auto",
    headless: bool = False,
    api_url: str = "",
    ml_url: str = "",
) -> Dict[str, Any]:
    """
    Executa a carga e cadastro no Portal Fake a partir da Planilha Mestra.
    """
    print("\n" + "=" * 70)
    print(f"💻 [PROCESSO 4] INICIANDO CADASTRO NO PORTAL FAKE (Modo: {modo.upper()})")
    print("=" * 70)

    configurar_logs(PASTA_LOGS)
    planilha = Path(caminho_planilha) if caminho_planilha else PLANILHA_PADRAO
    PASTA_SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    # 1. Carregar usuários da planilha
    print(f"\n[Etapa 1] Lendo registros aprovados da Planilha Mestra: {planilha.name}")
    try:
        usuarios = carregar_usuarios(planilha)
    except Exception as exc:
        print(f"❌ Falha ao carregar a planilha mestra: {exc}")
        return {"total_candidatos": 0, "cadastrados": 0, "falhas": 0, "evidencia": None}

    if not usuarios:
        print("⚠️ Nenhum registro com status aprovado encontrado na planilha mestra.")
        return {"total_candidatos": 0, "cadastrados": 0, "falhas": 0, "evidencia": None}

    lista_processar = usuarios[:quantidade] if quantidade > 0 else usuarios
    total = len(lista_processar)
    print(f"  • {total} cliente(s) selecionado(s) para cadastro.")

    cadastrados = 0
    falhas_lista: List[Dict[str, str]] = []
    caminho_evidencia: Path | None = None

    # 2. Execução API (se solicitada ou configurada)
    api_url = api_url or os.getenv("CADASTRO_API_URL", "")
    ml_url = ml_url or os.getenv("CADASTRO_ML_URL", "")

    if modo in ("api", "auto") and api_url:
        print(f"\n[Etapa 2] Executando cadastro via API ({api_url})...")
        cadastrados, falhas_lista = cadastrar_usuarios_api(lista_processar, api_url, ml_url)
        print(f"  • Cadastrados via API: {cadastrados}/{total}")

    # 3. Execução RPA via Playwright (se modo rpa ou fallback do auto)
    deve_rodar_rpa = modo == "rpa" or (modo == "auto" and (not api_url or falhas_lista))
    itens_rpa = falhas_lista if (modo == "auto" and api_url) else lista_processar

    if deve_rodar_rpa and itens_rpa:
        print(f"\n[Etapa 2] Executando cadastro no Portal Fake via Playwright RPA...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_DATA_DIR),
                headless=headless,
            )
            page = context.new_page()
            url_portal = f"file://{INDEX_HTML.resolve()}"
            print(f"  🌐 Acessando Portal Fake: {url_portal}")
            page.goto(url_portal)

            sucessos_rpa, falhas_rpa = preencher_portal_rapido(
                page, itens_rpa, qtd=len(itens_rpa)
            )
            cadastrados += sucessos_rpa
            falhas_lista = falhas_rpa

            # Captura evidência fotográfica do portal preenchido
            caminho_evidencia = salvar_evidencia_cadastros(page, PASTA_SCREENSHOTS)
            context.close()

    print("\n" + "=" * 70)
    print("📊 [PROCESSO 4] RESUMO DO CADASTRO NO PORTAL:")
    print(f"  • Total Candidatos: {total}")
    print(f"  • Cadastrados com Sucesso: {cadastrados}")
    print(f"  • Falhas: {len(falhas_lista)}")
    if caminho_evidencia:
        print(f"  📸 Evidência salva em: {caminho_evidencia}")
    print("=" * 70 + "\n")

    return {
        "total_candidatos": total,
        "cadastrados": cadastrados,
        "falhas": len(falhas_lista),
        "evidencia": caminho_evidencia,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 4 - Cadastro Automatizado no Portal Fake a partir da Planilha Mestra"
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        default=str(PLANILHA_PADRAO),
        help="Caminho do arquivo .xlsx (padrão: resources/planilha_mestra.xlsx).",
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=0,
        help="Quantidade máxima de cadastros (0 para todos).",
    )
    parser.add_argument(
        "--modo",
        choices=["auto", "api", "rpa"],
        default="auto",
        help="Modo de execução: auto (API com fallback RPA), api ou rpa.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o navegador em modo oculto.",
    )

    args = parser.parse_args()
    executar_processo_4(
        caminho_planilha=args.planilha,
        quantidade=args.quantidade,
        modo=args.modo,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
