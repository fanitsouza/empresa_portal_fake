import argparse
import datetime
import logging
from pathlib import Path
import random
import sys
from typing import List, Tuple


# Adiciona dinamicamente a pasta 'source' ao sys.path para funcionar de qualquer diretório
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


try:
    from processo_atendimento.gestor_arquivos import GestorArquivos
    from processo_atendimento.leitor_email import LeitorEmailIMAP
    from processo_atendimento.portal_integracao import PortalERPIntegracao
    from processo_atendimento.resposta_cliente import RespostaClienteSMTP
    from processo_atendimento.validador_docs import ValidadorDocs
except ImportError:
    from gestor_arquivos import GestorArquivos
    from leitor_email import LeitorEmailIMAP
    from portal_integracao import PortalERPIntegracao
    from resposta_cliente import RespostaClienteSMTP
    from validador_docs import ValidadorDocs


logger = logging.getLogger("ORQUESTRADOR")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")


class OrquestradorProcessoAtendimento:
    """Orquestrador principal do Processo 1 - Setor de Atendimento ao Cliente."""

    def __init__(self, raiz_projeto: Path | None = None) -> None:
        self.gestor = GestorArquivos(raiz_projeto)
        self.leitor = LeitorEmailIMAP(self.gestor)
        self.validador = ValidadorDocs()
        self.portal = PortalERPIntegracao(self.gestor.raiz_erp.parent.parent)
        self.resposta = RespostaClienteSMTP()

    def _gerar_protocolo(self) -> str:
        """Gera protocolo único no formato #2026-XXXX."""
        sufixo = random.randint(1000, 9999)
        ano = datetime.datetime.now().year
        return f"#{ano}-{sufixo}"

    def criar_exemplo_simulacao(self) -> List[Tuple[Path, str]]:
        """Cria arquivos PDF de simulação para execução local sem dependência de e-mail live."""
        logger.info("[ORQUESTRADOR] Gerando arquivos de simulação na pasta Downloads/...")
        
        pdf_aprovado = self.gestor.pasta_downloads / "solicitacao_completa_ana_silva.pdf"
        texto_aprovado = (
            "Ficha Cadastral Assinada\n"
            "Nome: Ana Silva\n"
            "CPF: 111.222.333-44\n"
            "E-mail: ana.silva@exemplo.com\n"
            "Documento Oficial com Foto: Carteira de Identidade RG 1234567-SSP\n"
            "Comprovante de Residência: Conta de Luz referente ao endereço Rua A, 100\n"
            "Assinatura do Cliente: Ana Silva\n"
        )
        pdf_aprovado.write_text(texto_aprovado, encoding="utf-8")

        pdf_pendente = self.gestor.pasta_downloads / "solicitacao_pendente_carlos_souza.pdf"
        texto_pendente = (
            "Ficha Cadastral Assinada\n"
            "Nome: Carlos Souza\n"
            "CPF: 999.888.777-66\n"
            "E-mail: carlos.souza@exemplo.com\n"
            "Assinatura do Cliente: Carlos Souza\n"
            # Ausentes: Documento Foto e Comprovante de Residência
        )
        pdf_pendente.write_text(texto_pendente, encoding="utf-8")

        return [
            (pdf_aprovado, "ana.silva@exemplo.com"),
            (pdf_pendente, "carlos.souza@exemplo.com"),
        ]

    def executar_fluxo(self, modo: str = "simulacao", headless: bool = True) -> int:
        """
        Executa o fluxo completo do Processo 1:
        1. Garantir estrutura de pastas local
        2. Ler e-mails / baixar PDFs
        3. Para cada PDF:
           - Validação documental pypdf
           - Se APROVADO: mover Documentos_OK/ -> Cadastrar ERP Playwright -> mover Encaminhados/ -> E-mail Sucesso
           - Se PENDENTE: mover Documentos_Pendentes/ -> E-mail Pendência
        """
        logger.info("=" * 70)
        logger.info(f"[ORQUESTRADOR] Iniciando Execução do Processo 1 (Modo: {modo.upper()})")
        logger.info("=" * 70)

        # 1. Estrutura de pastas
        self.gestor.garantir_estrutura_diretorios()

        # 2. Leitura de e-mails / obtenção dos PDFs
        if modo == "real":
            itens_processar = self.leitor.ler_emails_pendentes()
        else:
            itens_processar = self.criar_exemplo_simulacao()

        if not itens_processar:
            logger.info("[ORQUESTRADOR] Nenhuma nova solicitação/anexo para processar.")
            return 0

        logger.info(f"[ORQUESTRADOR] {len(itens_processar)} arquivo(s) PDF para processar.")
        processados_com_sucesso = 0

        # 3. Processamento de cada PDF
        for caminho_pdf, email_remetente in itens_processar:
            if not caminho_pdf.exists():
                logger.warning(f"[ORQUESTRADOR] Arquivo ignorado (não encontrado): {caminho_pdf}")
                continue

            protocolo = self._gerar_protocolo()
            logger.info("-" * 60)
            logger.info(f"[ORQUESTRADOR] Processando arquivo: {caminho_pdf.name} | Protocolo: {protocolo}")

            # a. Validação documental via pypdf
            aprovado, pendencias, dados_cliente = self.validador.validar_documentos_pdf(caminho_pdf)
            
            # Atualiza e-mail do cliente se extraído ou usa do remetente
            if email_remetente and email_remetente != "cliente@example.com":
                dados_cliente["email"] = email_remetente

            if aprovado:
                logger.info(f"[ORQUESTRADOR] Fluxo APROVAÇÃO iniciado para {dados_cliente.get('nome')}.")

                # Mover PDF para Documentos_OK/
                pdf_ok = self.gestor.mover_para_documentos_ok(caminho_pdf)

                # Cadastrar no ERP via Playwright
                sucesso_erp = self.portal.cadastrar_cliente_erp(dados_cliente, headless=headless)

                if sucesso_erp:
                    # Mover PDF para Encaminhados/ após cadastro concluído no ERP
                    self.gestor.mover_para_encaminhados(pdf_ok)

                # Enviar e-mail de Sucesso ao cliente
                self.resposta.enviar_resposta_cliente(
                    email_destino=dados_cliente.get("email", email_remetente),
                    aprovado=True,
                    protocolo=protocolo,
                    dados_cliente=dados_cliente,
                )
                processados_com_sucesso += 1

            else:
                logger.info(f"[ORQUESTRADOR] Fluxo PENDÊNCIA iniciado para {dados_cliente.get('nome')}.")

                # Mover PDF para Documentos_Pendentes/
                self.gestor.mover_para_documentos_pendentes(caminho_pdf)

                # Enviar e-mail de Pendência ao cliente com a lista de pendências
                self.resposta.enviar_resposta_cliente(
                    email_destino=dados_cliente.get("email", email_remetente),
                    aprovado=False,
                    protocolo=protocolo,
                    pendencias=pendencias,
                    dados_cliente=dados_cliente,
                )

        logger.info("=" * 70)
        logger.info(f"[ORQUESTRADOR] Execução do Processo 1 finalizada. Total processados: {len(itens_processar)}")
        logger.info("=" * 70)

        return processados_com_sucesso


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automação Completa do Processo 1 (Setor de Atendimento ao Cliente) - Portal Fake"
    )
    parser.add_argument(
        "--modo",
        choices=["simulacao", "real"],
        default="simulacao",
        help="Modo de execução: 'simulacao' (arquivos locais) ou 'real' (leitura de e-mail IMAP live).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Executa a automação Playwright com janela de navegador visível.",
    )

    args = parser.parse_args()

    orquestrador = OrquestradorProcessoAtendimento()
    orquestrador.executar_fluxo(modo=args.modo, headless=not args.no_headless)


if __name__ == "__main__":
    main()
