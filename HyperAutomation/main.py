#!/usr/bin/env python3
"""
Orquestrador Principal / CLI Unificado - Portal Fake Soluções Digitais
Disciplina: Técnicas de Hyperautomation

Permite executar:
1. Processos Isolados:
   - Processo 1: Envio de Fichas para Assinatura
   - Processo 2: Baixar e Validar Documentação Recebida
   - Processo 3: Extrair Dados do PDF e Atualizar Planilha Mestra
   - Processo 4: Cadastrar Clientes no Portal Fake via Planilha

2. Pipelines Integrados / Encadeados:
   - validacao-extracao (Processo 2 + Processo 3)
   - atendimento-completo (Processo 2 + Processo 3 + Processo 4)
   - completo (Processo 1 + Processo 2 + Processo 3 + Processo 4)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Configuração dinâmica dos caminhos
ROOT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = ROOT_DIR / "source"
if not SOURCE_DIR.exists():
    # Se main.py estiver na raiz do repositório
    SOURCE_DIR = ROOT_DIR / "HyperAutomation" / "source"

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_1_envio_fichas import executar_processo_1
from processo_2_validacao_docs import executar_processo_2
from processo_3_extracao_planilha import executar_processo_3
from processo_4_cadastro_portal import executar_processo_4


def menu_interativo() -> None:
    """Exibe menu interativo no terminal quando nenhum argumento for passado."""
    print("=" * 70)
    print("       🏢 PORTAL FAKE SOLUÇÕES DIGITAIS - HYPERAUTOMATION")
    print("                 PAINEL DE CONTROLE DE PROCESSOS")
    print("=" * 70)
    print("Escolha uma opção de execução:")
    print()
    print("  [1] Processo 1: Gerar e Enviar Ficha para Assinatura (E-mail)")
    print("  [2] Processo 2: Baixar e Validar Documentação Recebida (Gmail)")
    print("  [3] Processo 3: Extrair Dados de PDFs e Salvar na Planilha Mestra")
    print("  [4] Processo 4: Cadastrar Clientes no Portal Fake via Planilha")
    print()
    print("  [5] Pipeline Integrado: Processo 2 + 3 (Validar ➔ Extrair na Planilha)")
    print("  [6] Pipeline Completo de Atendimento: Processo 2 + 3 + 4 (Validar ➔ Planilha ➔ Portal)")
    print("  [7] Pipeline Total: Processo 1 + 2 + 3 + 4 (Ciclo Completo)")
    print("  [0] Sair")
    print("=" * 70)

    try:
        escolha = input("\n👉 Digite o número da opção desejada: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.")
        return

    if escolha == "1":
        executar_processo_1(modo="unico", row_index=0)
    elif escolha == "2":
        executar_processo_2(modo="real")
    elif escolha == "3":
        executar_processo_3(somente_local=True)
    elif escolha == "4":
        executar_processo_4(headless=False)
    elif escolha == "5":
        executar_pipeline_validacao_extracao(modo="real")
    elif escolha == "6":
        executar_pipeline_atendimento_completo(modo="real", headless=False)
    elif escolha == "7":
        executar_pipeline_total(modo="real", headless=False)
    elif escolha == "0":
        print("Encerrando.")
    else:
        print("Opção inválida.")


def executar_pipeline_validacao_extracao(modo: str = "real") -> None:
    """Executa Processo 2 e passa os PDFs aprovados diretamente para o Processo 3."""
    print("\n" + "#" * 70)
    print("⚡ EXECUTANDO PIPELINE: VALIDAÇÃO + EXTRAÇÃO (Processo 2 + 3)")
    print("#" * 70)

    # 1. Executa Processo 2
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 2. Executa Processo 3 com os PDFs aprovados
    if aprovados:
        print("\n🔗 Conectando com Processo 3 para extração dos dados...")
        executar_processo_3(lista_pdfs=aprovados)
    else:
        print("\nℹ️ Nenhum novo documento aprovado no Processo 2 para alimentar o Processo 3.")


def executar_pipeline_atendimento_completo(modo: str = "real", headless: bool = False) -> None:
    """Executa Processo 2 ➔ Processo 3 ➔ Processo 4."""
    print("\n" + "#" * 70)
    print("⚡ EXECUTANDO PIPELINE: ATENDIMENTO COMPLETO (Processos 2 + 3 + 4)")
    print("#" * 70)

    # 1. Processo 2: Baixar e Validar
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 2. Processo 3: Extrair e Planilha
    if aprovados:
        print("\n🔗 Conectando com Processo 3 para atualizar a Planilha Mestra...")
        res_proc3 = executar_processo_3(lista_pdfs=aprovados)
        
        # 3. Processo 4: Cadastro no Portal
        if res_proc3.get("sucessos", 0) > 0 or res_proc3.get("adicionados", 0) > 0 or res_proc3.get("atualizados", 0) > 0:
            print("\n🔗 Conectando com Processo 4 para realizar o cadastro no Portal Fake...")
            executar_processo_4(headless=headless)
    else:
        print("\nℹ️ Nenhum novo documento aprovado no Processo 2.")


def executar_pipeline_total(modo: str = "real", headless: bool = False) -> None:
    """Executa todo o fluxo (1 ao 4)."""
    print("\n" + "#" * 70)
    print("🌟 EXECUTANDO PIPELINE TOTAL (Processos 1 + 2 + 3 + 4)")
    print("#" * 70)

    # 1. Processo 1
    executar_processo_1(modo="unico", row_index=0)

    # 2. Processo 2
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 3. Processo 3
    if aprovados:
        executar_processo_3(lista_pdfs=aprovados)
        # 4. Processo 4
        executar_processo_4(headless=headless)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Portal Fake Soluções Digitais - Hyperautomation Orchestrator CLI"
    )
    parser.add_argument(
        "--processo",
        choices=["1", "2", "3", "4"],
        help="Executa um processo isolado (1: Envio, 2: Validação, 3: Extração/Planilha, 4: Cadastro).",
    )
    parser.add_argument(
        "--pipeline",
        choices=["validacao-extracao", "atendimento-completo", "completo", "2_3", "2_3_4", "1_2_3_4"],
        help="Executa um pipeline encadeado de processos.",
    )
    parser.add_argument(
        "--modo",
        choices=["real", "simulacao"],
        default="real",
        help="Modo de execução (real: e-mail live, simulacao: arquivos locais de teste).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa navegadores em modo oculto (sem abrir janela).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Força exibição visual da janela do navegador.",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Linha específica para o Processo 1 (padrão: 0).",
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=0,
        help="Quantidade limite de registros para o Processo 4 (0 para todos).",
    )

    args = parser.parse_args()

    # Se nenhum argumento foi informado, abre o menu interativo
    if not args.processo and not args.pipeline:
        menu_interativo()
        return

    is_headless = args.headless and not args.no_headless

    # 1. Execuções Isoladas
    if args.processo == "1":
        executar_processo_1(modo="unico", row_index=args.row_index, headless=is_headless)
    elif args.processo == "2":
        executar_processo_2(modo=args.modo)
    elif args.processo == "3":
        executar_processo_3(somente_local=(args.modo == "simulacao"))
    elif args.processo == "4":
        executar_processo_4(quantidade=args.quantidade, headless=is_headless)

    # 2. Execuções em Pipeline
    elif args.pipeline in ("validacao-extracao", "2_3"):
        executar_pipeline_validacao_extracao(modo=args.modo)
    elif args.pipeline in ("atendimento-completo", "2_3_4"):
        executar_pipeline_atendimento_completo(modo=args.modo, headless=is_headless)
    elif args.pipeline in ("completo", "1_2_3_4"):
        executar_pipeline_total(modo=args.modo, headless=is_headless)


if __name__ == "__main__":
    main()
