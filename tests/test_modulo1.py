"""
Testes Automatizados - Processo 1 (Atendimento & Validação de Documentos)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "HyperAutomation" / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_atendimento.validador_docs import ValidadorDocs


def test_validador_docs_instancia():
    """Valida se o validador de documentos é instanciado com regras corretas."""
    validador = ValidadorDocs()
    assert hasattr(validador, "REGRAS_DOCUMENTOS")
    assert "Ficha Cadastral Assinada" in validador.REGRAS_DOCUMENTOS
    assert "Documento Oficial com Foto" in validador.REGRAS_DOCUMENTOS
    assert "Comprovante de Residência" in validador.REGRAS_DOCUMENTOS


def test_validador_regras_palavras_chave():
    """Valida se as palavras-chave obrigatórias estão presentes nas regras."""
    validador = ValidadorDocs()
    regras = validador.REGRAS_DOCUMENTOS
    assert any("ficha" in kw.lower() for kw in regras["Ficha Cadastral Assinada"])
    assert any("rg" in kw.lower() or "cnh" in kw.lower() for kw in regras["Documento Oficial com Foto"])
    assert any("residencia" in kw.lower() or "luz" in kw.lower() or "agua" in kw.lower() for kw in regras["Comprovante de Residência"])
