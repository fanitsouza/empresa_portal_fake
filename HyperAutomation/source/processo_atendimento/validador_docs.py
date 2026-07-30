import logging
from pathlib import Path
import re
from typing import Dict, List, Tuple

logger = logging.getLogger("VALIDAÇÃO")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

# Importa pypdf com tratamento gracioso de fallback caso pypdf não esteja instalado
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False
        PdfReader = None  # type: ignore


class ValidadorDocs:
    """Inspeciona PDFs unificados e valida a presença dos 3 documentos obrigatórios."""

    REGRAS_DOCUMENTOS = {
        "Ficha Cadastral Assinada": ["ficha", "cadastral", "assinatura", "dados"],
        "Documento Oficial com Foto": ["identidade", "rg", "cpf", "carteira", "motorista"],
        "Comprovante de Residência": ["comprovante", "residencia", "endereco", "endereço", "conta", "luz", "agua"],
    }

    def _extrair_texto_pdf(self, caminho_pdf: Path) -> str:
        """Extrai o texto bruto de todas as páginas do PDF."""
        if not caminho_pdf.exists() or not caminho_pdf.is_file():
            logger.error(f"[VALIDAÇÃO] Arquivo PDF não encontrado: {caminho_pdf}")
            return ""

        texto_completo = []

        if HAS_PYPDF and PdfReader is not None:
            try:
                reader = PdfReader(str(caminho_pdf))
                for idx, page in enumerate(reader.pages):
                    texto_pagina = page.extract_text() or ""
                    texto_completo.append(texto_pagina)
                return "\n".join(texto_completo)
            except Exception as erro:
                logger.warning(f"[VALIDAÇÃO] Erro ao ler PDF com pypdf ({erro}). Usando leitor textual de fallback.")

        # Fallback para arquivos de texto/simulação se pypdf não estiver disponível ou falhar
        try:
            return caminho_pdf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # Se for binário e sem pypdf, tenta inferir pelo nome do arquivo
            return caminho_pdf.name

    def _extrair_dados_cliente(self, texto: str, caminho_pdf: Path) -> Dict[str, str]:
        """Extrai Nome, CPF e E-mail a partir do texto do PDF usando Regex ou padrões."""
        # Extração de CPF (11 dígitos formatados ou sequenciais)
        cpf_match = re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", texto)
        cpf = re.sub(r"\D", "", cpf_match.group(0)) if cpf_match else "12345678900"

        # Extração de E-mail
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", texto)
        email = email_match.group(0) if email_match else "cliente@example.com"

        # Extração de Nome
        nome_match = re.search(r"(?:Nome|Cliente|Nome Completo)[\s:]+([A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç ]+)", texto)
        if nome_match:
            nome_bruto = nome_match.group(1).strip().split("\n")[0]
            nome_partes = [p for p in nome_bruto.split() if len(p) > 1]
            nome = " ".join(nome_partes[:3]) if nome_partes else "Cliente Demonstração"
        else:
            # Tenta inferir nome pelo stem do arquivo ou default
            stem_limpo = re.sub(r"[^\w\s]", " ", caminho_pdf.stem).strip()
            nome = stem_limpo.title() if len(stem_limpo) > 3 else "Cliente Demonstração"

        return {
            "nome": nome,
            "cpf": cpf,
            "email": email,
        }

    def validar_documentos_pdf(
        self, caminho_pdf: Path
    ) -> Tuple[bool, List[str], Dict[str, str]]:
        """
        Valida a presença dos 3 documentos obrigatórios no PDF.

        Retorna:
        - (True, [], dados_cliente) se todos os 3 documentos estiverem presentes.
        - (False, pendencias, dados_cliente) se faltar algum documento.
        """
        logger.info(f"[VALIDAÇÃO] Iniciando inspeção documental em: {caminho_pdf.name}")

        texto_pdf = self._extrair_texto_pdf(caminho_pdf).lower()
        dados_cliente = self._extrair_dados_cliente(texto_pdf, caminho_pdf)

        pendencias: List[str] = []

        for doc_nome, palavras_chave in self.REGRAS_DOCUMENTOS.items():
            encontrado = False

            if doc_nome == "Documento Oficial com Foto":
                # Exige pelo menos uma das palavras da foto (rg, cpf, identidade, etc)
                encontrado = any(palavra in texto_pdf for palavra in palavras_chave)
            elif doc_nome == "Ficha Cadastral Assinada":
                # Exige pelo menos uma palavra chave de ficha cadastral
                encontrado = any(palavra in texto_pdf for palavra in palavras_chave)
            elif doc_nome == "Comprovante de Residência":
                # Exige pelo menos uma palavra de comprovante de residência
                encontrado = any(palavra in texto_pdf for palavra in palavras_chave)

            if not encontrado:
                logger.warning(f"[VALIDAÇÃO] Documento ausente: {doc_nome}")
                pendencias.append(doc_nome)
            else:
                logger.info(f"[VALIDAÇÃO] Documento verificado com sucesso: {doc_nome}")

        aprovado = len(pendencias) == 0

        if aprovado:
            logger.info(f"[VALIDAÇÃO] RESULTADO: APROVADO. Todos os 3 documentos obrigatórios foram encontrados.")
        else:
            logger.warning(f"[VALIDAÇÃO] RESULTADO: PENDENTE. Faltam {len(pendencias)} documento(s): {', '.join(pendencias)}")

        return aprovado, pendencias, dados_cliente
