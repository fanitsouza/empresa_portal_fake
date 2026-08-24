import email
from email.header import decode_header
import imaplib
import logging
import os
from pathlib import Path
import re
from typing import List, Tuple

import sys

SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from dotenv import load_dotenv

try:
    from processo_atendimento.gestor_arquivos import GestorArquivos
except ImportError:
    from gestor_arquivos import GestorArquivos


logger = logging.getLogger("LEITOR_EMAIL")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

def carregar_env() -> None:
    path_atual = Path(__file__).resolve()
    candidatos = [
        path_atual.parents[1] / ".env",
        path_atual.parents[2] / ".env",
        path_atual.parents[3] / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "HyperAutomation" / "source" / ".env",
    ]
    for env_path in candidatos:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break
    else:
        load_dotenv()

carregar_env()


class LeitorEmailIMAP:
    """Monitora caixa de e-mails via IMAP4_SSL, extrai anexos PDF e aplica a flag \\Seen."""

    def __init__(self, gestor: GestorArquivos | None = None) -> None:
        self.gestor = gestor or GestorArquivos()
        self.host = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
        self.port = int(os.getenv("IMAP_PORT", "993"))
        self.email_remetente = (os.getenv("EMAIL_REMETENTE") or "").strip()
        self.senha_app = (os.getenv("EMAIL_SENHA_APP") or os.getenv("EMAIL_SENHA") or "").strip()


    def _decodificar_texto(self, texto_bruto: str | bytes) -> str:
        """Decodifica cabeçalhos codificados em e-mails."""
        if not texto_bruto:
            return ""
        if isinstance(texto_bruto, bytes):
            return texto_bruto.decode("utf-8", errors="replace")
        partes = decode_header(texto_bruto)
        resultado = []
        for pedaco, codificacao in partes:
            if isinstance(pedaco, bytes):
                resultado.append(pedaco.decode(codificacao or "utf-8", errors="replace"))
            else:
                resultado.append(str(pedaco))
        return "".join(resultado)

    def _extrair_email_remetente(self, campo_from: str) -> str:
        """Extrai apenas o endereço de e-mail do campo From."""
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", campo_from)
        if match:
            return match.group(0)
        return campo_from.strip()

    def ler_emails_pendentes(
        self, termos_busca: List[str] | None = None
    ) -> List[Tuple[Path, str]]:
        """
        Conecta ao IMAP, busca e-mails NÃO LIDOS (UNSEEN) contendo termos de busca no assunto,
        baixa os anexos PDF para a pasta Downloads/ do gestor local e marca o e-mail como visto (\\Seen).

        Retorna uma lista de tuplas: [(caminho_pdf_baixado, email_remetente), ...]
        """
        termos_busca = termos_busca or ["Assinatura", "Ficha", "Atendimento", "Documentos"]

        if not self.email_remetente or not self.senha_app:
            logger.warning(
                "[LEITOR EMAIL] Credenciais EMAIL_REMETENTE / EMAIL_SENHA_APP não configuradas no .env. "
                "Retornando arquivos presentes na pasta Downloads/ como fallback de simulação."
            )
            return self._fallback_downloads_locais()

        resultados: List[Tuple[Path, str]] = []

        try:
            logger.info(f"[LEITOR EMAIL] Conectando ao servidor IMAP {self.host}:{self.port}...")
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.email_remetente, self.senha_app)
            mail.select("INBOX")

            # Busca e-mails não lidos
            status, mensagens_ids = mail.search(None, "UNSEEN")
            if status != "OK" or not mensagens_ids[0]:
                logger.info("[LEITOR EMAIL] Nenhum novo e-mail não lido (UNSEEN) encontrado na INBOX.")
                mail.logout()
                return resultados

            ids_lista = mensagens_ids[0].split()
            logger.info(f"[LEITOR EMAIL] Encontrados {len(ids_lista)} e-mail(s) não lido(s).")

            for msg_id in ids_lista:
                status, dados = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = dados[0][1]
                msg = email.message_from_bytes(raw_email)

                assunto = self._decodificar_texto(msg.get("Subject", ""))
                remetente_raw = self._decodificar_texto(msg.get("From", ""))
                email_remetente = self._extrair_email_remetente(remetente_raw)

                # Verifica se assunto contém algum dos termos de busca
                contem_termo = any(termo.lower() in assunto.lower() for termo in termos_busca)
                if not contem_termo:
                    logger.debug(f"[LEITOR EMAIL] E-mail ignorado (assunto fora dos termos): {assunto}")
                    continue

                logger.info(f"[LEITOR EMAIL] Processando e-mail de {email_remetente} | Assunto: {assunto}")

                # Extrai anexos PDF
                anexos_baixados = 0
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    if part.get("Content-Disposition") is None:
                        continue

                    filename = part.get_filename()
                    if filename:
                        filename = self._decodificar_texto(filename)
                        if filename.lower().endswith(".pdf"):
                            caminho_temp = self.gestor.pasta_downloads / filename
                            caminho_temp.write_bytes(part.get_payload(decode=True))
                            resultados.append((caminho_temp, email_remetente))
                            anexos_baixados += 1
                            logger.info(f"[LEITOR EMAIL] Anexo baixado com sucesso: {filename}")

                # Aplica a flag \Seen imediatamente no e-mail lido para evitar duplicidades
                mail.store(msg_id, "+FLAGS", "\\Seen")
                logger.info(f"[LEITOR EMAIL] Flag \\Seen aplicada ao e-mail ID {msg_id.decode()}.")

            mail.logout()

        except Exception as erro:
            logger.error(f"[LEITOR EMAIL] Erro durante a conexão ou leitura IMAP: {erro}")
            return self._fallback_downloads_locais()

        return resultados

    def _fallback_downloads_locais(self) -> List[Tuple[Path, str]]:
        """Fallback local: retorna arquivos PDF que já estejam na pasta Downloads/."""
        arquivos = list(self.gestor.pasta_downloads.glob("*.pdf"))
        logger.info(f"[LEITOR EMAIL] Fallback local encontrou {len(arquivos)} arquivo(s) PDF em Downloads/.")
        return [(arq, "cliente@example.com") for arq in arquivos]
