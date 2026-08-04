from __future__ import annotations

import imaplib
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.policy import default
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv


LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


class FalhaConsultaEmailError(Exception):
    """Falha ao consultar mensagens por IMAP."""


class FalhaAutenticacaoIMAPError(FalhaConsultaEmailError):
    """Falha de autenticacao no servidor IMAP."""


class PastaDocumentosInvalidaError(Exception):
    """Pasta de documentos inexistente ou invalida."""


class NenhumPDFEncontradoError(Exception):
    """Nenhum PDF encontrado na pasta configurada."""


class IMAPClient(Protocol):
    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        ...

    def select(self, mailbox: str) -> tuple[str, list[bytes]]:
        ...

    def search(self, charset: str | None, criterion: str) -> tuple[str, list[bytes]]:
        ...

    def fetch(self, message_id: bytes, query: str) -> tuple[str, list[object]]:
        ...

    def logout(self) -> tuple[str, list[bytes]]:
        ...


@dataclass(frozen=True)
class ConfiguracaoIMAP:
    remetente: str
    senha: str
    host: str = "imap.gmail.com"
    port: int = 993
    caixa: str = "INBOX"
    palavra_aprovado: str = "aprovado"
    somente_nao_lidos: bool = True

    @classmethod
    def carregar_do_ambiente(cls) -> "ConfiguracaoIMAP":
        """Carrega configuracoes de IMAP sem expor credenciais em logs."""
        load_dotenv(ENV_PATH)

        remetente = os.getenv("EMAIL_REMETENTE", "").strip()
        senha = os.getenv("EMAIL_SENHA", "")

        if not remetente:
            raise FalhaConsultaEmailError("EMAIL_REMETENTE nao configurado.")
        if not senha:
            raise FalhaConsultaEmailError("EMAIL_SENHA nao configurada.")

        try:
            port = int(os.getenv("IMAP_PORT", "993"))
        except ValueError as exc:
            raise FalhaConsultaEmailError("IMAP_PORT deve ser um numero inteiro.") from exc

        return cls(
            remetente=remetente,
            senha=senha,
            host=os.getenv("IMAP_HOST", "imap.gmail.com").strip() or "imap.gmail.com",
            port=port,
            caixa=os.getenv("IMAP_CAIXA", "INBOX").strip() or "INBOX",
            palavra_aprovado=(
                os.getenv("IMAP_PALAVRA_APROVADO", "aprovado").strip() or "aprovado"
            ),
            somente_nao_lidos=_env_bool(os.getenv("IMAP_SOMENTE_NAO_LIDOS", "true")),
        )


@dataclass(frozen=True)
class ResultadoBuscaEmail:
    emails_analisados: int
    pdfs_baixados: int
    arquivos: list[Path]


def garantir_pasta_documentos(pasta: str | Path) -> Path:
    """Cria a pasta de documentos aprovados quando necessario."""
    caminho = Path(pasta)
    if caminho.exists() and not caminho.is_dir():
        raise PastaDocumentosInvalidaError(
            f"A pasta de documentos e invalida: {caminho}"
        )

    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def localizar_pdfs_aprovados(pasta: str | Path) -> list[Path]:
    """Localiza PDFs recursivamente na pasta de documentos aprovados."""
    caminho = garantir_pasta_documentos(pasta)
    pdfs = sorted(arquivo for arquivo in caminho.rglob("*.pdf") if arquivo.is_file())

    if not pdfs:
        raise NenhumPDFEncontradoError(f"Nenhum PDF encontrado em: {caminho}")

    return pdfs


def baixar_pdfs_aprovados_por_imap(
    pasta_destino: str | Path,
    configuracao: ConfiguracaoIMAP | None = None,
    imap_factory: type[imaplib.IMAP4_SSL] = imaplib.IMAP4_SSL,
) -> ResultadoBuscaEmail:
    """Consulta e-mails aprovados via IMAP/SSL e baixa anexos PDF."""
    pasta = garantir_pasta_documentos(pasta_destino)
    config = configuracao or ConfiguracaoIMAP.carregar_do_ambiente()

    LOGGER.info(
        "Consultando e-mails aprovados via IMAP em %s:%s caixa %s",
        config.host,
        config.port,
        config.caixa,
    )

    cliente: IMAPClient | None = None
    arquivos_baixados: list[Path] = []
    emails_analisados = 0

    try:
        cliente = imap_factory(config.host, config.port)
    except Exception as exc:
        raise FalhaConsultaEmailError(
            f"Falha ao conectar ao servidor IMAP {config.host}:{config.port}: {exc}"
        ) from exc

    try:
        try:
            cliente.login(config.remetente, config.senha)
        except imaplib.IMAP4.error as exc:
            raise FalhaAutenticacaoIMAPError(
                "Falha de autenticacao IMAP. Verifique EMAIL_REMETENTE e EMAIL_SENHA."
            ) from exc

        status, _ = cliente.select(config.caixa)
        _validar_status_imap(status, f"Falha ao selecionar a caixa {config.caixa}.")

        criterio = "UNSEEN" if config.somente_nao_lidos else "ALL"
        status, dados_busca = cliente.search(None, criterio)
        _validar_status_imap(status, "Falha ao buscar mensagens por IMAP.")

        ids_mensagens = dados_busca[0].split() if dados_busca and dados_busca[0] else []

        for mensagem_id in ids_mensagens:
            status, dados_mensagem = cliente.fetch(mensagem_id, "(BODY.PEEK[])")
            _validar_status_imap(status, "Falha ao carregar mensagem por IMAP.")

            mensagem = _parse_mensagem(dados_mensagem)
            if mensagem is None:
                continue

            emails_analisados += 1
            if not _mensagem_contem_palavra(mensagem, config.palavra_aprovado):
                continue

            arquivos_baixados.extend(_salvar_anexos_pdf(mensagem, pasta))

    except FalhaConsultaEmailError:
        raise
    except imaplib.IMAP4.error as exc:
        raise FalhaConsultaEmailError(f"Falha ao consultar e-mail via IMAP: {exc}") from exc
    except OSError as exc:
        raise FalhaConsultaEmailError(f"Falha de conexao IMAP: {exc}") from exc
    finally:
        if cliente is not None:
            try:
                cliente.logout()
            except Exception:
                LOGGER.debug("Falha ao encerrar sessao IMAP.", exc_info=True)

    LOGGER.info("E-mails analisados: %s", emails_analisados)
    LOGGER.info("PDFs baixados por IMAP: %s", len(arquivos_baixados))

    return ResultadoBuscaEmail(
        emails_analisados=emails_analisados,
        pdfs_baixados=len(arquivos_baixados),
        arquivos=arquivos_baixados,
    )


def _salvar_anexos_pdf(mensagem: Message, pasta: Path) -> list[Path]:
    arquivos: list[Path] = []

    for parte in mensagem.walk():
        nome_arquivo = parte.get_filename()
        if not nome_arquivo:
            continue

        nome_arquivo = _decodificar_cabecalho(nome_arquivo)
        if Path(nome_arquivo).suffix.lower() != ".pdf":
            continue

        conteudo = parte.get_payload(decode=True)
        if not conteudo:
            continue

        caminho_seguro = _caminho_unico(pasta, _sanitizar_nome_arquivo(nome_arquivo))
        caminho_seguro.write_bytes(conteudo)
        arquivos.append(caminho_seguro)
        LOGGER.info("Anexo PDF salvo: %s", caminho_seguro.name)

    return arquivos


def _parse_mensagem(dados_mensagem: list[object]) -> Message | None:
    for item in dados_mensagem:
        if isinstance(item, tuple) and isinstance(item[1], bytes):
            return message_from_bytes(item[1], policy=default)
    return None


def _mensagem_contem_palavra(mensagem: Message, palavra: str) -> bool:
    termo = _normalizar_texto(palavra)
    assunto = _normalizar_texto(_decodificar_cabecalho(mensagem.get("Subject", "")))
    corpo = _normalizar_texto(_extrair_corpo_texto(mensagem))
    return termo in assunto or termo in corpo


def _extrair_corpo_texto(mensagem: Message) -> str:
    partes: list[str] = []

    if mensagem.is_multipart():
        for parte in mensagem.walk():
            if parte.get_content_maintype() == "multipart":
                continue
            if parte.get_filename():
                continue
            if parte.get_content_type() not in {"text/plain", "text/html"}:
                continue
            partes.append(_conteudo_texto(parte))
    else:
        partes.append(_conteudo_texto(mensagem))

    return "\n".join(partes)


def _conteudo_texto(parte: Message) -> str:
    try:
        conteudo = parte.get_content()
    except Exception:
        payload = parte.get_payload(decode=True)
        if not payload:
            return ""
        charset = parte.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    return conteudo if isinstance(conteudo, str) else ""


def _decodificar_cabecalho(valor: str) -> str:
    partes = decode_header(valor)
    texto = ""
    for conteudo, charset in partes:
        if isinstance(conteudo, bytes):
            texto += conteudo.decode(charset or "utf-8", errors="replace")
        else:
            texto += conteudo
    return texto


def _caminho_unico(pasta: Path, nome_arquivo: str) -> Path:
    candidato = pasta / nome_arquivo
    if not candidato.exists():
        return candidato

    base = candidato.stem
    sufixo = candidato.suffix
    contador = 1
    while True:
        novo_candidato = pasta / f"{base}_{contador}{sufixo}"
        if not novo_candidato.exists():
            return novo_candidato
        contador += 1


def _sanitizar_nome_arquivo(nome_arquivo: str) -> str:
    nome = Path(nome_arquivo).name
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome)
    return nome or "documento.pdf"


def _validar_status_imap(status: str, mensagem: str) -> None:
    if status.upper() != "OK":
        raise FalhaConsultaEmailError(mensagem)


def _normalizar_texto(valor: str) -> str:
    valor = unicodedata.normalize("NFD", valor)
    valor = "".join(caractere for caractere in valor if unicodedata.category(caractere) != "Mn")
    return valor.lower()


def _env_bool(valor: str) -> bool:
    return valor.strip().lower() in {"1", "true", "sim", "yes", "y"}

