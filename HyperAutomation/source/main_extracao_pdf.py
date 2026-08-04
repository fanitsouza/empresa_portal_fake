from __future__ import annotations

import argparse
import logging
from pathlib import Path

from extracao_pdf import processar_pdfs, salvar_resultados_json
from localizador_documentos import (
    FalhaConsultaEmailError,
    NenhumPDFEncontradoError,
    baixar_pdfs_aprovados_por_imap,
    garantir_pasta_documentos,
    localizar_pdfs_aprovados,
)


BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
PASTA_PADRAO = PATH_ROOT / "resources" / "Documentos_Aprovados"
SAIDA_PADRAO = PATH_ROOT / "resources" / "saida_extracao_pdf.json"

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Baixa, processa PDFs aprovados e gera JSON com os dados extraidos."""
    configurar_logs()
    argumentos = criar_parser().parse_args()

    pasta_documentos = resolver_caminho(argumentos.pasta, PASTA_PADRAO)
    caminho_saida = resolver_caminho(argumentos.saida, SAIDA_PADRAO)

    LOGGER.info("Iniciando extracao de documentos PDF.")
    garantir_pasta_documentos(pasta_documentos)

    erro_email: str | None = None
    if not argumentos.somente_local:
        try:
            resumo_email = baixar_pdfs_aprovados_por_imap(pasta_documentos)
            LOGGER.info("Quantidade de e-mails analisados: %s", resumo_email.emails_analisados)
            LOGGER.info("Quantidade de PDFs baixados: %s", resumo_email.pdfs_baixados)
        except FalhaConsultaEmailError as exc:
            erro_email = str(exc)
            LOGGER.error("Consulta de e-mail falhou: %s", erro_email)
    else:
        LOGGER.info("Execucao local solicitada; consulta IMAP nao sera realizada.")

    try:
        pdfs = localizar_pdfs_aprovados(pasta_documentos)
    except NenhumPDFEncontradoError as exc:
        LOGGER.error("%s", exc)
        salvar_resultados_json([], caminho_saida)
        print("Resumo final:")
        print("  PDFs encontrados: 0")
        print("  JSON gerado:", caminho_saida)
        if erro_email:
            print("  Falha na consulta de e-mail:", erro_email)
        return 1

    LOGGER.info("PDFs localizados para processamento: %s", len(pdfs))
    resultados = processar_pdfs(pdfs)
    salvar_resultados_json(resultados, caminho_saida)

    sucessos = sum(1 for resultado in resultados if resultado["sucesso"])
    falhas = len(resultados) - sucessos

    LOGGER.info("Processamento finalizado.")
    print("Resumo final:")
    print(f"  PDFs encontrados: {len(pdfs)}")
    print(f"  Processados com sucesso: {sucessos}")
    print(f"  Processados com falha: {falhas}")
    print(f"  JSON gerado: {caminho_saida}")
    if erro_email:
        print(f"  Falha na consulta de e-mail: {erro_email}")

    return 0 if sucessos or resultados else 1


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extracao de dados de PDFs aprovados."
    )
    parser.add_argument(
        "--somente-local",
        action="store_true",
        help="Processa apenas PDFs ja existentes na pasta configurada.",
    )
    parser.add_argument(
        "--pasta",
        default=None,
        help="Pasta dos PDFs aprovados. Caminhos relativos usam a raiz HyperAutomation.",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Arquivo JSON de saida. Caminhos relativos usam a raiz HyperAutomation.",
    )
    return parser


def resolver_caminho(valor: str | None, padrao: Path) -> Path:
    if not valor:
        return padrao

    caminho = Path(valor)
    if caminho.is_absolute():
        return caminho
    return PATH_ROOT / caminho


def configurar_logs() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


if __name__ == "__main__":
    raise SystemExit(main())

