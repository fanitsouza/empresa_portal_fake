"""
Testes Automatizados - Processo 4 (SAC - Serviço de Atendimento ao Cliente)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "HyperAutomation" / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_sac import gerar_protocolo_sac, GeradorEmailSAC


def test_geracao_protocolo_sac():
    """Valida o formato padrão dos protocolos emitidos pelo SAC."""
    protocolo = gerar_protocolo_sac()
    assert protocolo.startswith("#SAC-")
    assert len(protocolo.split("-")) == 3


def test_geracao_templates_email_sac():
    """Valida a geração dos templates HTML de confirmação e de erro."""
    gerador = GeradorEmailSAC()
    cliente_mock = {
        "cpf": "123.456.789-00",
        "email": "cliente@teste.com",
        "telefone": "(11) 98765-4321",
        "endereco": "Rua Teste, 100",
    }
    
    html_sucesso = gerador.gerar_html_confirmacao_sucesso("Carlos Silva", "#SAC-2026-1234", cliente_mock)
    assert "CADASTRO CONCLUÍDO COM SUCESSO" in html_sucesso
    assert "Carlos Silva" in html_sucesso
    assert "#SAC-2026-1234" in html_sucesso

    html_erro = gerador.gerar_html_notificacao_erro("Carlos Silva", "#SAC-2026-1234", "CPF Duplicado", cliente_mock)
    assert "INCONSISTÊNCIA IDENTIFICADA" in html_erro
    assert "CPF Duplicado" in html_erro
