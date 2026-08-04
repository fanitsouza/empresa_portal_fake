from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError


LOGGER = logging.getLogger(__name__)

CAMPO_NOME = "Nome"
CAMPO_CPF = "CPF"
CAMPO_EMAIL = "E-mail"
CAMPO_TELEFONE = "Telefone"
CAMPO_NASCIMENTO = "Nascimento"
CAMPO_ENDERECO = "Endereco"

CAMPOS_OBRIGATORIOS = [
    CAMPO_NOME,
    CAMPO_CPF,
    CAMPO_EMAIL,
    CAMPO_TELEFONE,
    CAMPO_NASCIMENTO,
    CAMPO_ENDERECO,
]


class ExtracaoPDFError(Exception):
    """Erro base da extracao de PDFs."""


class ArquivoInexistenteError(ExtracaoPDFError):
    """Arquivo informado nao existe."""


class ArquivoNaoPdfError(ExtracaoPDFError):
    """Arquivo informado nao possui extensao PDF."""


class PDFInvalidoError(ExtracaoPDFError):
    """PDF invalido ou ilegivel."""


class PDFProtegidoError(ExtracaoPDFError):
    """PDF protegido por senha."""


class PDFSemTextoPesquisavelError(ExtracaoPDFError):
    """PDF sem texto pesquisavel."""


class CamposObrigatoriosAusentesError(ExtracaoPDFError):
    """Campos obrigatorios nao encontrados no texto extraido."""

    def __init__(self, campos_ausentes: list[str], dados: dict[str, str]) -> None:
        self.campos_ausentes = campos_ausentes
        self.dados = dados
        mensagem = (
            "Campos obrigatorios nao encontrados: "
            + ", ".join(campos_ausentes)
        )
        super().__init__(mensagem)


@dataclass(frozen=True)
class ResultadoPDF:
    """Resultado estruturado de um PDF processado."""

    arquivo: str
    sucesso: bool
    dados: dict[str, str]
    campos_ausentes: list[str]
    erro: str | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "arquivo": self.arquivo,
            "sucesso": self.sucesso,
            "dados": self.dados,
            "campos_ausentes": self.campos_ausentes,
            "erro": self.erro,
        }


ROTULOS_CAMPOS = {
    CAMPO_NOME: ("Nome completo", "Nome"),
    CAMPO_CPF: ("CPF",),
    CAMPO_EMAIL: ("E-mail", "Email"),
    CAMPO_TELEFONE: ("Telefone", "Celular"),
    CAMPO_NASCIMENTO: ("Data de nascimento", "Nascimento"),
    CAMPO_ENDERECO: ("Endereco completo", "Endereco", "Endereço completo", "Endereço"),
}

EMAIL_REGEX = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
CPF_REGEX = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
DATA_REGEX = re.compile(r"\b(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b")


def extrair_texto_pdf(caminho_pdf: str | Path) -> str:
    """Abre um PDF e extrai o texto pesquisavel de todas as paginas."""
    caminho = Path(caminho_pdf)
    validar_arquivo_pdf(caminho)

    try:
        leitor = PdfReader(str(caminho))
    except PdfReadError as exc:
        raise PDFInvalidoError(f"PDF invalido ou nao pode ser lido: {exc}") from exc
    except Exception as exc:
        raise PDFInvalidoError(f"Falha ao abrir o PDF: {exc}") from exc

    if leitor.is_encrypted:
        raise PDFProtegidoError("PDF protegido por senha.")

    partes_texto: list[str] = []
    try:
        for pagina in leitor.pages:
            texto_pagina = pagina.extract_text() or ""
            partes_texto.append(texto_pagina)
    except Exception as exc:
        raise PDFInvalidoError(f"Falha ao extrair texto do PDF: {exc}") from exc

    texto = "\n".join(partes_texto).strip()
    if not texto:
        raise PDFSemTextoPesquisavelError(
            "O PDF nao possui texto pesquisavel e pode exigir OCR."
        )

    return texto


def validar_arquivo_pdf(caminho: Path) -> None:
    """Valida existencia e extensao do arquivo PDF."""
    if not caminho.exists():
        raise ArquivoInexistenteError(f"Arquivo inexistente: {caminho}")

    if not caminho.is_file():
        raise ArquivoInexistenteError(f"O caminho informado nao e um arquivo: {caminho}")

    if caminho.suffix.lower() != ".pdf":
        raise ArquivoNaoPdfError(f"O arquivo nao possui extensao .pdf: {caminho.name}")


def extrair_campos_texto(texto: str) -> dict[str, str]:
    """Identifica e normaliza os campos obrigatorios a partir do texto extraido."""
    linhas = [linha.strip() for linha in texto.splitlines()]
    dados = {campo: "" for campo in CAMPOS_OBRIGATORIOS}

    for indice, linha in enumerate(linhas):
        if not linha:
            continue

        for campo, rotulos in ROTULOS_CAMPOS.items():
            valor = _extrair_valor_rotulado(linha, rotulos)
            if valor is None:
                continue

            if not _valor_preenchido(valor):
                valor = _proxima_linha_com_valor(linhas, indice + 1)

            if valor and not dados[campo]:
                dados[campo] = _normalizar_valor(campo, valor)

    _aplicar_regex_fallbacks(texto, dados)
    return dados


def validar_campos_obrigatorios(dados: dict[str, str]) -> list[str]:
    """Retorna a lista dos campos obrigatorios ausentes."""
    return [campo for campo in CAMPOS_OBRIGATORIOS if not dados.get(campo, "").strip()]


def processar_pdf(caminho_pdf: str | Path) -> dict[str, Any]:
    """Processa um PDF e retorna sucesso, dados, campos ausentes e erro."""
    caminho = Path(caminho_pdf)
    arquivo = str(caminho)
    LOGGER.info("Processando PDF: %s", caminho.name)

    try:
        texto = extrair_texto_pdf(caminho)
        dados = extrair_campos_texto(texto)
        campos_ausentes = validar_campos_obrigatorios(dados)

        if campos_ausentes:
            raise CamposObrigatoriosAusentesError(campos_ausentes, dados)

        LOGGER.info("PDF processado com sucesso: %s", caminho.name)
        return ResultadoPDF(
            arquivo=arquivo,
            sucesso=True,
            dados=dados,
            campos_ausentes=[],
            erro=None,
        ).para_dict()

    except CamposObrigatoriosAusentesError as exc:
        LOGGER.warning(
            "PDF com campos ausentes: %s | %s",
            caminho.name,
            ", ".join(exc.campos_ausentes),
        )
        return ResultadoPDF(
            arquivo=arquivo,
            sucesso=False,
            dados=exc.dados,
            campos_ausentes=exc.campos_ausentes,
            erro=str(exc),
        ).para_dict()

    except ExtracaoPDFError as exc:
        LOGGER.error("Falha ao processar PDF %s: %s", caminho.name, exc)
        return ResultadoPDF(
            arquivo=arquivo,
            sucesso=False,
            dados={},
            campos_ausentes=CAMPOS_OBRIGATORIOS.copy(),
            erro=str(exc),
        ).para_dict()

    except Exception as exc:
        LOGGER.exception("Falha inesperada ao processar PDF %s", caminho.name)
        return ResultadoPDF(
            arquivo=arquivo,
            sucesso=False,
            dados={},
            campos_ausentes=CAMPOS_OBRIGATORIOS.copy(),
            erro=f"Falha inesperada ao processar PDF: {exc}",
        ).para_dict()


def processar_pdfs(caminhos_pdf: list[Path]) -> list[dict[str, Any]]:
    """Processa uma lista de PDFs sem interromper por erro em arquivo individual."""
    return [processar_pdf(caminho) for caminho in caminhos_pdf]


def salvar_resultados_json(resultados: list[dict[str, Any]], caminho_saida: str | Path) -> Path:
    """Salva a lista de resultados em JSON para consumo posterior."""
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", encoding="utf-8") as arquivo_json:
        json.dump(resultados, arquivo_json, ensure_ascii=False, indent=4)

    LOGGER.info("JSON de extracao gerado em: %s", caminho)
    return caminho


def _extrair_valor_rotulado(linha: str, rotulos: tuple[str, ...]) -> str | None:
    for rotulo in rotulos:
        padrao = re.compile(
            rf"^\s*(?:\d+[\).]\s*)?{re.escape(rotulo)}\s*[:\-]?\s*(.*)$",
            re.IGNORECASE,
        )
        correspondencia = padrao.match(linha)
        if correspondencia:
            return correspondencia.group(1).strip()
    return None


def _proxima_linha_com_valor(linhas: list[str], indice_inicial: int) -> str:
    for linha in linhas[indice_inicial:]:
        if not _valor_preenchido(linha):
            continue
        if _linha_e_rotulo(linha):
            return ""
        return linha.strip()
    return ""


def _linha_e_rotulo(linha: str) -> bool:
    for rotulos in ROTULOS_CAMPOS.values():
        if _extrair_valor_rotulado(linha, rotulos) is not None:
            return True
    return False


def _valor_preenchido(valor: str) -> bool:
    valor_limpo = valor.strip()
    return bool(valor_limpo) and not set(valor_limpo) <= {"_", "-", ".", " "}


def _normalizar_valor(campo: str, valor: str) -> str:
    valor = re.sub(r"\s+", " ", valor).strip(" :-\t")

    if campo == CAMPO_CPF:
        return _formatar_cpf(valor)
    if campo == CAMPO_EMAIL:
        encontrado = EMAIL_REGEX.search(valor)
        return encontrado.group(0).lower() if encontrado else valor.lower()
    if campo == CAMPO_TELEFONE:
        return _formatar_telefone(valor)
    if campo == CAMPO_NASCIMENTO:
        return _formatar_data(valor)

    return valor


def _aplicar_regex_fallbacks(texto: str, dados: dict[str, str]) -> None:
    if not dados[CAMPO_CPF]:
        correspondencia = CPF_REGEX.search(texto)
        if correspondencia:
            dados[CAMPO_CPF] = _formatar_cpf(correspondencia.group(0))

    if not dados[CAMPO_EMAIL]:
        correspondencia = EMAIL_REGEX.search(texto)
        if correspondencia:
            dados[CAMPO_EMAIL] = correspondencia.group(0).lower()

    if not dados[CAMPO_NASCIMENTO]:
        correspondencia = DATA_REGEX.search(texto)
        if correspondencia:
            dados[CAMPO_NASCIMENTO] = _formatar_data(correspondencia.group(0))


def _formatar_cpf(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11:
        return valor.strip()
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def _formatar_telefone(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return valor.strip()


def _formatar_data(valor: str) -> str:
    valor = valor.strip()
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", valor)
    if iso:
        ano, mes, dia = iso.groups()
        return f"{dia}/{mes}/{ano}"
    return valor.replace("-", "/")
