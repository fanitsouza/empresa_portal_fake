"""
Testes Automatizados - Processo 2 (Organização de Dados & Planilha Mestra)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "HyperAutomation" / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from extracao_pdf import _formatar_cpf, _formatar_telefone, _formatar_data, extrair_campos_texto
from planilha_mestra import carregar_registros_planilha


def test_normalizacao_campos():
    """Valida funções de sanitização e formatação de campos extraídos."""
    assert _formatar_cpf("123.456.789-00") == "123.456.789-00"
    assert _formatar_cpf("12345678900") == "123.456.789-00"
    
    assert _formatar_telefone("11987654321") == "(11) 98765-4321"
    assert _formatar_telefone("(11) 98765-4321") == "(11) 98765-4321"


def test_extrair_campos_texto():
    """Valida se o extrator localiza dados estruturados em texto de formulário."""
    texto_mock = """
    Nome Completo: Carlos Eduardo Pereira
    CPF: 123.456.789-10
    E-mail: carlos.pereira@exemplo.com
    Telefone: (11) 98765-4321
    Data de Nascimento: 15/05/1990
    Endereço: Av. Paulista, 1000 - São Paulo/SP
    """
    dados = extrair_campos_texto(texto_mock)
    assert dados.get("Nome") == "Carlos Eduardo Pereira"
    assert dados.get("CPF") == "123.456.789-10"
    assert dados.get("E-mail") == "carlos.pereira@exemplo.com"


def test_leitura_planilha_mestra():
    """Verifica se a leitura da planilha mestra carrega registros válidos."""
    caminho_planilha = BASE_DIR / "HyperAutomation" / "resources" / "planilha_mestra.xlsx"
    if caminho_planilha.exists():
        registros = carregar_registros_planilha(caminho_planilha)
        assert isinstance(registros, list)
