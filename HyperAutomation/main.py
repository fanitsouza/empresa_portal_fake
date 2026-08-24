#!/usr/bin/env python3
"""
Orquestrador Principal / CLI Unificado - Portal Fake Soluções Digitais
Disciplina: Técnicas de Hyperautomation

Arquitetura Completa de 5 Processos (BPMN):
  - Processo 1: Setor de Atendimento (Envio de Fichas e Recepção/Validação de 3 Documentos)
  - Processo 2: Organização de Dados (Extração Estruturada dos PDFs e Planilha Mestra .xlsx)
  - Processo 3: Setor de Cadastro (Consulta Prévia de CPF e Cadastro no Portal Fake)
  - Processo 4: Setor de SAC (E-mails de Sucesso/Inconsistência e Planilha Status_SAC)
  - Processo 5: Relatórios e Gerência (Consolidação, Indicadores, PDF Executivo e Envio ao Gerente)
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
from processo_3_extracao_planilha import executar_processo_3 as executar_processo_organizacao
from processo_4_cadastro_portal import executar_processo_3 as executar_processo_cadastro, executar_processo_4
from processo_sac import executar_processo_sac
from processo_relatorios import executar_processo_5 as executar_processo_relatorios


def menu_interativo() -> None:
    """Exibe menu interativo no terminal quando nenhum argumento for passado."""
    print("=" * 78)
    print("         🏢 PORTAL FAKE SOLUÇÕES DIGITAIS - HYPERAUTOMATION")
    print("                   PAINEL DE CONTROLE DE PROCESSOS (BPMN)")
    print("=" * 78)
    print("Escolha uma opção de execução:")
    print()
    print("  --- PROCESSOS ISOLADOS ---")
    print("  [1] Processo 1: Atendimento - Gerar/Enviar Ficha e Validar Documentos")
    print("  [2] Processo 2: Organização de Dados - Extrair PDFs e Atualizar Planilha Mestra")
    print("  [3] Processo 3: Setor de Cadastro - Consultar CPF e Cadastrar no Portal Fake")
    print("  [4] Processo 4: Setor de SAC - E-mails de Sucesso/Erro e Planilha Status_SAC")
    print("  [5] Processo 5: Relatórios e Gerência - Indicadores, PDF Executivo e Drive")
    print()
    print("  --- PIPELINES INTEGRADAS / ENCADEADAS ---")
    print("  [6] Pipeline: Validação + Extração (Processos 1 + 2)")
    print("  [7] Pipeline: Cadastro + SAC + Relatórios (Processos 3 + 4 + 5)")
    print("  [8] Pipeline: Atendimento Completo (Validar ➔ Planilha ➔ Cadastro ➔ SAC ➔ Relatório)")
    print("  [9] Pipeline Total de Ponta a Ponta (Processos 1 ➔ 2 ➔ 3 ➔ 4 ➔ 5)")
    print()
    print("  [0] Sair")
    print("=" * 78)

    try:
        escolha = input("\n👉 Digite o número da opção desejada: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.")
        return

    if escolha == "1":
        executar_processo_1(modo="unico", row_index=0)
        executar_processo_2(modo="real")
    elif escolha == "2":
        executar_processo_organizacao(somente_local=True)
    elif escolha == "3":
        executar_processo_cadastro(headless=False)
    elif escolha == "4":
        executar_processo_sac()
    elif escolha == "5":
        executar_processo_relatorios()
    elif escolha == "6":
        executar_pipeline_validacao_extracao(modo="real")
    elif escolha == "7":
        executar_pipeline_cadastro_sac_relatorios(headless=False)
    elif escolha == "8":
        executar_pipeline_atendimento_completo(modo="real", headless=False)
    elif escolha == "9":
        executar_pipeline_total(modo="real", headless=False)
    elif escolha == "0":
        print("Encerrando.")
    else:
        print("Opção inválida.")


def executar_pipeline_validacao_extracao(modo: str = "real") -> None:
    """Executa Processo 1/2 e passa os PDFs aprovados diretamente para a Organização de Dados."""
    print("\n" + "#" * 78)
    print("⚡ EXECUTANDO PIPELINE: VALIDAÇÃO + EXTRAÇÃO (Processos 1 + 2)")
    print("#" * 78)

    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    if aprovados:
        print("\n🔗 Conectando com Processo 2 para extração dos dados...")
        executar_processo_organizacao(lista_pdfs=aprovados)
    else:
        print("\nℹ️ Nenhum novo documento aprovado no Processo 1 para alimentar o Processo 2.")


def executar_pipeline_cadastro_sac_relatorios(headless: bool = False, enviar_email: bool = True) -> None:
    """Executa Cadastro no Portal Fake ➔ SAC ➔ Relatórios para a Gerência."""
    print("\n" + "#" * 78)
    print("⚡ EXECUTANDO PIPELINE: CADASTRO + SAC + RELATÓRIOS (Processos 3 + 4 + 5)")
    print("#" * 78)

    # 1. Cadastro no Portal
    res_cad = executar_processo_cadastro(headless=headless)
    resultados_cad = res_cad.get("resultados", [])

    # 2. SAC
    if resultados_cad:
        print("\n🔗 Conectando com o Setor de SAC para envio de notificações...")
        executar_processo_sac(resultados_processo_3=resultados_cad, enviar_email=enviar_email)
    else:
        executar_processo_sac(enviar_email=enviar_email)

    # 3. Relatórios e Gerência
    print("\n🔗 Conectando com o Setor de Relatórios e Gerência...")
    executar_processo_relatorios(enviar_email=enviar_email)


def executar_pipeline_atendimento_completo(modo: str = "real", headless: bool = False, enviar_email: bool = True) -> None:
    """Executa Processo 1 ➔ Processo 2 ➔ Processo 3 ➔ Processo 4 ➔ Processo 5."""
    print("\n" + "#" * 78)
    print("⚡ EXECUTANDO PIPELINE: ATENDIMENTO COMPLETO (Processos 1 a 5)")
    print("#" * 78)

    # 1. Validação Documental
    res_proc2 = executar_processo_2(modo=modo)
    aprovados = res_proc2.get("aprovados", [])

    # 2. Extração e Planilha Mestra
    if aprovados:
        print("\n🔗 Conectando com Organização de Dados (Extração)...")
        executar_processo_organizacao(lista_pdfs=aprovados)

    # 3. Cadastro no Portal
    print("\n🔗 Conectando com Setor de Cadastro...")
    res_cad = executar_processo_cadastro(headless=headless)

    # 4. SAC
    print("\n🔗 Conectando com Setor de SAC...")
    executar_processo_sac(resultados_processo_3=res_cad.get("resultados"), enviar_email=enviar_email)

    # 5. Relatórios e Gerência
    print("\n🔗 Conectando com Setor de Relatórios e Gerência...")
    executar_processo_relatorios(enviar_email=enviar_email)


def executar_pipeline_total(modo: str = "real", headless: bool = False, enviar_email: bool = True) -> None:
    """Executa todo o fluxo de ponta a ponta (Envio ➔ Validação ➔ Planilha ➔ Cadastro ➔ SAC ➔ Relatório)."""
    print("\n" + "#" * 78)
    print("🌟 EXECUTANDO PIPELINE TOTAL DE PONTA A PONTA (1 ao 5)")
    print("#" * 78)

    # 1. Envio de Ficha
    executar_processo_1(modo="unico", row_index=0)

    # 2 a 5. Continuação completa
    executar_pipeline_atendimento_completo(modo=modo, headless=headless, enviar_email=enviar_email)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Portal Fake Soluções Digitais - Hyperautomation Orchestrator CLI (BPMN 5 Processos)"
    )
    parser.add_argument(
        "--processo",
        choices=["1", "2", "3", "4", "5", "atendimento", "organizacao", "cadastro", "sac", "relatorios"],
        help="Executa um processo isolado (1: Atendimento, 2: Organização, 3: Cadastro, 4: SAC, 5: Relatórios).",
    )
    parser.add_argument(
        "--pipeline",
        choices=[
            "validacao-extracao", "cadastro-sac", "cadastro-sac-relatorios",
            "atendimento-completo", "completo", "1_2", "3_4_5", "1_2_3_4_5"
        ],
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
        "--email-gerente",
        default=None,
        help="E-mail do gerente para recebimento do relatório executivo.",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Desativa o disparo SMTP de e-mails, gravando apenas em arquivos/planilhas.",
    )

    args = parser.parse_args()

    # Se nenhum argumento foi informado, abre o menu interativo
    if not args.processo and not args.pipeline:
        menu_interativo()
        return

    is_headless = args.headless and not args.no_headless
    enviar_email = not args.no_email

    # 1. Execuções Isoladas
    if args.processo in ("1", "atendimento"):
        executar_processo_1(modo="unico", row_index=args.row_index, headless=is_headless)
        executar_processo_2(modo=args.modo)
    elif args.processo in ("2", "organizacao"):
        executar_processo_organizacao(somente_local=(args.modo == "simulacao"))
    elif args.processo in ("3", "cadastro"):
        executar_processo_cadastro(quantidade=args.quantidade, headless=is_headless)
    elif args.processo in ("4", "sac"):
        executar_processo_sac(email_teste=args.email, enviar_email=enviar_email)
    elif args.processo in ("5", "relatorios"):
        executar_processo_relatorios(email_gerente=args.email_gerente or args.email, enviar_email=enviar_email)

    # 2. Execuções em Pipeline
    elif args.pipeline in ("validacao-extracao", "1_2"):
        executar_pipeline_validacao_extracao(modo=args.modo)
    elif args.pipeline in ("cadastro-sac", "cadastro-sac-relatorios", "3_4_5"):
        executar_pipeline_cadastro_sac_relatorios(headless=is_headless, enviar_email=enviar_email)
    elif args.pipeline in ("atendimento-completo", "completo", "1_2_3_4_5"):
        executar_pipeline_atendimento_completo(modo=args.modo, headless=is_headless, enviar_email=enviar_email)


if __name__ == "__main__":
    main()
