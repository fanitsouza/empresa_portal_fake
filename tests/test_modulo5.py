"""
Testes Automatizados - Processo 5 (Relatórios e Gerência)
Portal Fake Soluções Digitais - Hyperautomation
"""
import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "HyperAutomation" / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from processo_relatorios import calcular_indicadores, gerar_html_relatorio_gerencial


def test_calculo_indicadores_kpi():
    """Valida o cálculo dos KPIs e status de SLA operacional."""
    dados_mock = {
        "clientes": [
            {"status_documental": "APROVADO", "status_cadastro": "SUCESSO", "status_sac": "CONFIRMACAO_ENVIADA"},
            {"status_documental": "APROVADO", "status_cadastro": "DUPLICADO", "status_sac": "NOTIFICACAO_ERRO_ENVIADA"},
            {"status_documental": "APROVADO", "status_cadastro": "SUCESSO", "status_sac": "CONFIRMACAO_ENVIADA"},
        ]
    }
    
    kpis = calcular_indicadores(dados_mock)
    assert kpis["total_solicitacoes"] == 3
    assert kpis["docs_aprovados"] == 3
    assert kpis["cadastros_sucesso"] == 2
    assert kpis["cadastros_duplicados"] == 1
    assert kpis["taxa_aprovacao_doc_pct"] == 100.0
    assert kpis["taxa_eficiencia_cadastro_pct"] == 66.7
    assert kpis["sla_status"] in ("EXCELENTE", "ESTÁVEL COM ATENÇÃO")


def test_geracao_html_relatorio():
    """Valida se o HTML gerado para o PDF contém os dados e indicadores consolidados."""
    dados_mock = {
        "clientes": [
            {
                "nome": "Ana Paula",
                "cpf_mascarado": "***.123.***-00",
                "status_cadastro": "SUCESSO",
                "status_sac": "CONFIRMACAO_ENVIADA",
                "protocolo_sac": "#SAC-2026-9999",
            }
        ]
    }
    kpis_mock = {
        "total_solicitacoes": 1,
        "taxa_aprovacao_doc_pct": 100.0,
        "taxa_eficiencia_cadastro_pct": 100.0,
        "taxa_resolucao_sac_pct": 100.0,
        "cadastros_sucesso": 1,
        "cadastros_duplicados": 0,
        "docs_aprovados": 1,
        "sla_status": "EXCELENTE",
        "sla_cor": "#16a34a",
        "sla_mensagem": "Operação perfeita.",
    }
    
    html = gerar_html_relatorio_gerencial(dados_mock, kpis_mock)
    assert "PORTAL FAKE SOLUÇÕES DIGITAIS" in html
    assert "Ana Paula" in html
    assert "#SAC-2026-9999" in html
    assert "100.0%" in html
