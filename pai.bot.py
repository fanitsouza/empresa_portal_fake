#!/usr/bin/env python3
"""
Orquestrador Principal (pai.bot.py) - Portal Fake Soluções Digitais
Disciplina: Técnicas de Hyperautomation - Roteiro 13
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bot import executar_todos_processos, main_cli

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        executar_todos_processos(headless=True, enviar_email=True)
