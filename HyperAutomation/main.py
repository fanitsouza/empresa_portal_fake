#!/usr/bin/env python3
"""
Orquestrador Principal / CLI Unificado - Portal Fake Soluções Digitais
Disciplina: Técnicas de Hyperautomation

Processos Integrados:
  - Processo 1: Gerar e Enviar Ficha de Cadastro para Assinatura (E-mail / DOCX)
  - Processo 2: Baixar e Validar Documentação Recebida (Gmail / IMAP - 3 docs obrigatórios)
  - Processo 3: Organização de Dados - Extrair Dados do PDF e Atualizar Planilha Mestra (.xlsx)
  - Processo 4: Setor de Cadastro - Consultar CPF, Cadastrar no Portal Fake e Validar
  - Processo 5: Setor de SAC - Notificações de Confirmação/Erro, Planilha Status_SAC e Exportação de Relatórios
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Configuração dinâmica dos caminhos
ROOT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = ROOT_DIR / "source"
if not SOURCE_DIR.exists():
    SOURCE_DIR = ROOT_DIR / "HyperAutomation" / "source"

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_1_envio_fichas import executar_processo_1
from processo_2_validacao_docs import executar_processo_2
from processo_3_extracao_planilha import executar_processo_3
from processo_4_cadastro_portal import executar_processo_3 as executar_processo_cadastro, executar_processo_4
from processo_sac import executar_processo_sac


def menu_interativo() -> None:
    """Exibe menu interativo no terminal quando nenhum argumento for passado."""
    print("=" * 75)
    print("       🏢 PORTAL FAKE SOLUÇÕES DIGITAIS - HYPERAUTOMATION")
    print("                 PAINEL DE CONTROLE DE PROCESSOS")
    print("=" * 75)
    print("Escolha uma opção de execução:")
    print()
    print("  --- PROCESSOS ISOLADOS ---")
    print("  [1] Processo 1: Gerar e Enviar Ficha para Assinatura (E-mail / DOCX)")
    print("  [2] Processo 2: Baixar e Validar Documentos Recebidos (Gmail / IMAP)")
    print("  [3] Processo 3: Extrair Dados de PDFs e Salvar na Planilha Mestra")
    print("  [4] Processo 4: Setor de Cadastro - Consultar CPF e Cadastrar no Portal Fake")
    print("  [5] Processo 5: Setor de SAC - Notificações de Sucesso/Erro e Planilha Status_SAC")
    print()
    print("  --- PIPELINES INTEGRADAS / ENCADEADAS ---")
    print("  [6] Pipeline: Validação + Extração (Processos 2 + 3)")
    print("  [7] Pipeline: Cadastro + SAC (Processos 4 + 5)")
    print("  [8] Pipeline: Atendimento Completo (Validar ➔ Planilha ➔ Cadastro ➔ SAC)")
    print("  [9] Pipeline Total de Ponta a Ponta (Processos 1 + 2 + 3 + 4 + 5)")
    print()
    print("  [0] Sair")
    print("=" * 75)

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
        executar_processo_cadastro(headless=False)
    elif escolha == "5":
        executar_processo_sac()
    elif escolha == "6":
        executar_pipeline_validacao_extracao(modo="real")
    elif escolha == "7":
        executar_pipeline_cadastro_sac(headless=False)
    elif escolha == "8":
        executar_pipeline_atendimento_completo(modo="real", headless=False)
    elif escolha == "9":
        executar_pipeline_total(modo="real", headless=False)
    elif escolha == "0":
        print("Encerrando.")
    else:
        print("Opção inválida.")


def executar_pipeline_validacao_extracao(modo: str = "real") -> None:
    """Executa Processo 2 e passa os PDFs aprovados diretamente para o Processo 3."""
    print("\n" + "#" * 75)
    print("⚡ EXECUTANDO PIPELINE: VALIDAÇÃO + EXTRAÇÃO (Processo 2 + 3)")
    print("#" * 75)

    # 1. Executa Processo 2
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 2. Executa Processo 3 com os PDFs aprovados
    if aprovados:
        print("\n🔗 Conectando com Processo 3 para extração dos dados...")
        executar_processo_3(lista_pdfs=aprovados)
    else:
        print("\nℹ️ Nenhum novo documento aprovado no Processo 2 para alimentar o Processo 3.")


def executar_pipeline_cadastro_sac(headless: bool = False) -> None:
    """Executa Cadastro no Portal Fake ➔ Disparos e Planilha no SAC."""
    print("\n" + "#" * 75)
    print("⚡ EXECUTANDO PIPELINE: CADASTRO + SAC (Processos 4 + 5)")
    print("#" * 75)

    # 1. Executa Cadastro no Portal
    res_cad = executar_processo_cadastro(headless=headless)
    resultados_cad = res_cad.get("resultados", [])

    # 2. Executa SAC com os resultados do cadastro
    if resultados_cad:
        print("\n🔗 Conectando com o Setor de SAC para envio de notificações e geração de Status_SAC...")
        executar_processo_sac(resultados_processo_3=resultados_cad)
    else:
        print("\nℹ️ Nenhum cadastro processado para acionamento do SAC.")


def executar_pipeline_atendimento_completo(modo: str = "real", headless: bool = False) -> None:
    """Executa Processo 2 ➔ Processo 3 ➔ Processo 4 (Cadastro) ➔ Processo 5 (SAC)."""
    print("\n" + "#" * 75)
    print("⚡ EXECUTANDO PIPELINE: ATENDIMENTO COMPLETO (Validar ➔ Planilha ➔ Cadastro ➔ SAC)")
    print("#" * 75)

    # 1. Processo 2: Baixar e Validar
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 2. Processo 3: Extrair e Planilha
    if aprovados:
        print("\n🔗 Conectando com Processo 3 para atualizar a Planilha Mestra...")
        res_proc3 = executar_processo_3(lista_pdfs=aprovados)
        
        # 3. Processo 4: Cadastro no Portal
        if res_proc3.get("sucessos", 0) > 0 or res_proc3.get("adicionados", 0) > 0 or res_proc3.get("atualizados", 0) > 0:
            print("\n🔗 Conectando com Processo de Cadastro no Portal Fake...")
            res_cad = executar_processo_cadastro(headless=headless)
            
            # 4. Processo 5: SAC
            if res_cad.get("resultados"):
                print("\n🔗 Conectando com o Setor de SAC...")
                executar_processo_sac(resultados_processo_3=res_cad["resultados"])
    else:
        print("\nℹ️ Nenhum novo documento aprovado no Processo 2. Executando SAC com base na planilha mestra...")
        executar_processo_sac()


def executar_pipeline_total(modo: str = "real", headless: bool = False) -> None:
    """Executa todo o fluxo de ponta a ponta (1 ao 5)."""
    print("\n" + "#" * 75)
    print("🌟 EXECUTANDO PIPELINE TOTAL (Processos 1 + 2 + 3 + 4 + 5)")
    print("#" * 75)

    # 1. Processo 1
    executar_processo_1(modo="unico", row_index=0)

    # 2. Processo 2
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 3. Processo 3
    if aprovados:
        executar_processo_3(lista_pdfs=aprovados)

    # 4. Processo 4 (Cadastro)
    res_cad = executar_processo_cadastro(headless=headless)

    # 5. Processo 5 (SAC)
    executar_processo_sac(resultados_processo_3=res_cad.get("resultados"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Portal Fake Soluções Digitais - Hyperautomation Orchestrator CLI"
    )
    parser.add_argument(
        "--processo",
        choices=["1", "2", "3", "4", "5", "sac", "cadastro", "envio", "validacao", "extracao"],
        help="Executa um processo isolado (1: Envio, 2: Validação, 3: Extração/Planilha, 4: Cadastro, 5: SAC).",
    )
    parser.add_argument(
        "--pipeline",
        choices=["validacao-extracao", "cadastro-sac", "atendimento-completo", "completo", "2_3", "4_5", "2_3_4_5", "1_2_3_4_5"],
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
        help="Quantidade limite de registros para processamento (0 para todos).",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="E-mail de destino customizado para teste dos disparos.",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Desativa o envio real de e-mails no SAC.",
    )

    args = parser.parse_args()

    # Se nenhum argumento foi informado, abre o menu interativo
    if not args.processo and not args.pipeline:
        menu_interativo()
        return

    is_headless = args.headless and not args.no_headless

    # 1. Execuções Isoladas
    if args.processo in ("1", "envio"):
        executar_processo_1(modo="unico", row_index=args.row_index, headless=is_headless)
    elif args.processo in ("2", "validacao"):
        executar_processo_2(modo=args.modo)
    elif args.processo in ("3", "extracao"):
        executar_processo_3(somente_local=(args.modo == "simulacao"))
    elif args.processo in ("4", "cadastro"):
        executar_processo_cadastro(quantidade=args.quantidade, headless=is_headless)
    elif args.processo in ("5", "sac"):
        executar_processo_sac(email_teste=args.email, enviar_email=not args.no_email)

    # 2. Execuções em Pipeline
    elif args.pipeline in ("validacao-extracao", "2_3"):
        executar_pipeline_validacao_extracao(modo=args.modo)
    elif args.pipeline in ("cadastro-sac", "4_5"):
        executar_pipeline_cadastro_sac(headless=is_headless)
    elif args.pipeline in ("atendimento-completo", "2_3_4_5"):
        executar_pipeline_atendimento_completo(modo=args.modo, headless=is_headless)
    elif args.pipeline in ("completo", "1_2_3_4_5"):
        executar_pipeline_total(modo=args.modo, headless=is_headless)


if __name__ == "__main__":
    main()
