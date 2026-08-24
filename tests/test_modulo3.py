"""
Testes Automatizados - Processo 3 (Setor de Cadastro no Portal Fake)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "HyperAutomation" / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_4_cadastro_portal import mascarar_cpf, extrair_nome_sobrenome


def test_mascarar_cpf():
    """Valida a aplicação de máscara de segurança no CPF."""
    assert mascarar_cpf("123.456.789-09") == "***.456.***-09"
    assert mascarar_cpf("12345678909") == "***.456.***-09"


def test_extrair_nomes():
    """Valida a separação entre primeiro nome e sobrenome completo para formulário."""
    nome, sobrenome = extrair_nome_sobrenome("João Pedro Almeida")
    assert nome == "João"
    assert sobrenome == "Pedro Almeida"
    
    nome_unico, sobrenome_unico = extrair_nome_sobrenome("Fani")
    assert nome_unico == "Fani"
    assert sobrenome_unico == "Fani"
