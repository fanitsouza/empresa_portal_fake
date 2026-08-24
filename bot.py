#!/usr/bin/env python3
"""
Orquestrador Principal (bot.py / pai.bot.py) - Portal Fake Soluções Digitais
Disciplina: Técnicas de Hyperautomation - Roteiro 13

Executa a solução completa integrando os 5 processos de ponta a ponta:
  Processo 1 (Atendimento) ➔ Processo 2 (Organização) ➔ Processo 3 (Cadastro) ➔ Processo 4 (SAC) ➔ Processo 5 (Relatórios)
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HYPER_DIR = BASE_DIR / "HyperAutomation"
SOURCE_DIR = HYPER_DIR / "source"

if str(HYPER_DIR) not in sys.path:
    sys.path.insert(0, str(HYPER_DIR))
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from main import main as main_cli, executar_pipeline_atendimento_completo

def executar_todos_processos(headless: bool = True, enviar_email: bool = True) -> None:
    """Executa a sequência completa de 1 a 5."""
    print("=" * 80)
    print("🤖 [BOT PRINCIPAL] INICIANDO EXECUÇÃO INTEGRADA DOS 5 PROCESSOS")
    print("=" * 80)
    executar_pipeline_atendimento_completo(modo="real", headless=headless, enviar_email=enviar_email)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        executar_todos_processos(headless=True, enviar_email=True)
