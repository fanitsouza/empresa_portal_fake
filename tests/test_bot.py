"""
Testes Automatizados - Integração Geral (bot.py / pai.bot.py)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import bot


def test_import_bot_principal():
    """Valida se os arquivos principais de orquestração estão íntegros e importáveis."""
    assert hasattr(bot, "executar_todos_processos")
    assert hasattr(bot, "main_cli")


def test_estrutura_diretorios_essenciais():
    """Valida se todas as pastas obrigatórias do ERP e recursos existem."""
    recursos = BASE_DIR / "HyperAutomation" / "resources"
    assert recursos.exists()
    assert (recursos / "portal_fake").exists()
    assert (recursos / "planilha_mestra.xlsx").exists()
