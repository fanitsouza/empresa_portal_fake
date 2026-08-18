"""
Processo 3 - Extração de Dados e Alimentação da Planilha Mestra
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Localizar ou receber os PDFs aprovados (do Processo 2 ou da pasta Documentos_Aprovados).
2. Extrair os campos cadastrais estruturados (Nome, CPF, E-mail, Telefone, Nascimento, Endereço).
3. Gerar o arquivo JSON intermediário com os dados extraídos.
4. Atualizar a Planilha Mestra (.xlsx) corporativa, evitando duplicidades por CPF.
5. Arquivar os PDFs processados na pasta ERP_Portal_Fake/Arquivados.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"

PASTA_PADRAO = RESOURCES_DIR / "Documentos_Aprovados"
SAIDA_PADRAO = RESOURCES_DIR / "saida_extracao_pdf.json"
PLANILHA_PADRAO = RESOURCES_DIR / "planilha_mestra.xlsx"
PASTA_ARQUIVADOS = RESOURCES_DIR / "ERP_Portal_Fake" / "Arquivados"

sys.path.append(str(BASE_DIR))

from extracao_pdf import processar_pdfs, salvar_resultados_json
from planilha_mestra import atualizar_planilha_mestra
from localizador_documentos import (
    FalhaConsultaEmailError,
    NenhumPDFEncontradoError,
    arquivar_pdfs_processados,
    baixar_pdfs_aprovados_por_imap,
    garantir_pasta_documentos,
    localizar_pdfs_aprovados,
)

LOGGER = logging.getLogger("PROCESSO_3_EXTRACAO")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(name)s] %(levelname)s: %(message)s")


def executar_processo_3(
    pasta_documentos: Path | str | None = None,
    caminho_planilha: Path | str | None = None,
    caminho_saida: Path | str | None = None,
    somente_local: bool = True,
    lista_pdfs: List[Path] | None = None,
) -> Dict[str, Any]:
    """
    Executa a extração dos PDFs e a atualização da Planilha Mestra.
    """
    print("\n" + "=" * 70)
    print("📊 [PROCESSO 3] INICIANDO EXTRAÇÃO DE DADOS E PLANILHA MESTRA")
    print("=" * 70)

    pasta_docs = Path(pasta_documentos) if pasta_documentos else PASTA_PADRAO
    planilha = Path(caminho_planilha) if caminho_planilha else PLANILHA_PADRAO
    saida_json = Path(caminho_saida) if caminho_saida else SAIDA_PADRAO

    garantir_pasta_documentos(pasta_docs)
    PASTA_ARQUIVADOS.mkdir(parents=True, exist_ok=True)

    # 1. Obtenção dos PDFs
    pdfs_para_processar: List[Path] = []

    if lista_pdfs:
        # Recebidos diretamente do Processo 2
        pdfs_para_processar = [p for p in lista_pdfs if p.exists() and p.suffix.lower() == ".pdf"]
        print(f"\n[Etapa 1] Recebidos {len(pdfs_para_processar)} PDF(s) aprovados do processo anterior.")
    else:
        # Busca por IMAP caso não seja somente local
        if not somente_local:
            print("\n[Etapa 1] Consultando e-mails IMAP para baixar PDFs aprovados...")
            try:
                resumo_email = baixar_pdfs_aprovados_por_imap(pasta_docs)
                print(f"  • E-mails analisados: {resumo_email.emails_analisados}")
                print(f"  • PDFs baixados: {resumo_email.pdfs_baixados}")
            except FalhaConsultaEmailError as exc:
                LOGGER.warning(f"Consulta IMAP falhou ou não configurada: {exc}")

        # Localiza arquivos locais
        print(f"\n[Etapa 1] Localizando arquivos PDF na pasta: {pasta_docs}")
        try:
            pdfs_para_processar = localizar_pdfs_aprovados(pasta_docs)
        except NenhumPDFEncontradoError:
            # Tenta também pasta do ERP Documentos_OK se existir
            pasta_erp_ok = RESOURCES_DIR / "ERP_Portal_Fake" / "Documentos_OK"
            if pasta_erp_ok.exists():
                pdfs_para_processar = list(pasta_erp_ok.glob("*.pdf"))

    if not pdfs_para_processar:
        print("\n⚠️ Nenhum PDF encontrado para extração.")
        salvar_resultados_json([], saida_json)
        return {
            "total_processados": 0,
            "sucessos": 0,
            "falhas": 0,
            "adicionados": 0,
            "atualizados": 0,
            "planilha": planilha,
            "json": saida_json,
        }

    print(f"\n[Etapa 2] Extraindo campos de {len(pdfs_para_processar)} arquivo(s) PDF...")
    resultados = processar_pdfs(pdfs_para_processar)

    # 2. Salvar JSON intermediário
    salvar_resultados_json(resultados, saida_json)
    print(f"  📄 JSON estruturado salvo em: {saida_json.name}")

    # 3. Atualizar Planilha Mestra
    print(f"\n[Etapa 3] Alimentando a Planilha Mestra (.xlsx)...")
    planilha_salva, adicionados, atualizados = atualizar_planilha_mestra(resultados, planilha)
    print(f"  📗 Planilha Mestra atualizada: {planilha_salva.name}")
    print(f"  ➕ Novos registros adicionados: {adicionados}")
    print(f"  🔄 Registros existentes atualizados: {atualizados}")

    # 4. Arquivar PDFs processados
    print(f"\n[Etapa 4] Movendo PDFs processados para a pasta Arquivados/...")
    arquivos_arquivados = arquivar_pdfs_processados(pdfs_para_processar, PASTA_ARQUIVADOS)
    print(f"  📦 {len(arquivos_arquivados)} arquivo(s) arquivado(s) com sucesso.")

    sucessos = sum(1 for r in resultados if r.get("sucesso"))
    falhas = len(resultados) - sucessos

    print("\n" + "=" * 70)
    print("📊 [PROCESSO 3] RESUMO DA EXTRAÇÃO:")
    print(f"  • Total de PDFs: {len(pdfs_para_processar)}")
    print(f"  • Extrações com Sucesso: {sucessos}")
    print(f"  • Extrações com Falha: {falhas}")
    print(f"  • Planilha Mestra: {planilha_salva}")
    print("=" * 70 + "\n")

    return {
        "total_processados": len(pdfs_para_processar),
        "sucessos": sucessos,
        "falhas": falhas,
        "adicionados": adicionados,
        "atualizados": atualizados,
        "planilha": planilha_salva,
        "json": saida_json,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 3 - Extração de Dados e Alimentação da Planilha Mestra"
    )
    parser.add_argument(
        "--pasta",
        default=None,
        help="Pasta com os PDFs aprovados (padrão: resources/Documentos_Aprovados).",
    )
    parser.add_argument(
        "--planilha",
        default=None,
        help="Caminho da Planilha Mestra .xlsx (padrão: resources/planilha_mestra.xlsx).",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Caminho do arquivo JSON de saída.",
    )
    parser.add_argument(
        "--somente-local",
        action="store_true",
        default=True,
        help="Processa apenas PDFs locais sem consultar IMAP (padrão: True).",
    )
    parser.add_argument(
        "--buscar-email",
        action="store_true",
        help="Conecta no IMAP para baixar novos PDFs aprovados antes de processar.",
    )

    args = parser.parse_args()
    somente_local = not args.buscar_email

    executar_processo_3(
        pasta_documentos=args.pasta,
        caminho_planilha=args.planilha,
        caminho_saida=args.saida,
        somente_local=somente_local,
    )


if __name__ == "__main__":
    main()
