from pathlib import Path
from atendimento.modelos import ResultadoValidacao


class ValidadorDocumentos:
    """Valida presença, extensão e tamanho dos documentos."""

    FORMATOS_PERMITIDOS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}

    DOCUMENTOS_OBRIGATORIOS = {
        "ficha_cadastro": ("ficha", "cadastro"),
        "documento_foto": ("rg", "cnh", "identidade", "documento"),
        "comprovante_residencia": ("comprovante", "residencia"),
    }

    NOMES_AMIGAVEIS = {
        "ficha_cadastro": "Ficha de cadastro preenchida",
        "documento_foto": "Documento oficial com foto",
        "comprovante_residencia": "Comprovante de residência",
    }

    def validar(self, anexos: list[Path]) -> ResultadoValidacao:
        resultado = ResultadoValidacao()
        anexos_validos = self._filtrar_arquivos_validos(anexos, resultado)

        for tipo, palavras_chave in self.DOCUMENTOS_OBRIGATORIOS.items():
            encontrado = self._localizar(anexos_validos, palavras_chave)
            if encontrado is None:
                resultado.pendencias.append(f"Ausente: {self.NOMES_AMIGAVEIS[tipo]}")
            else:
                resultado.documentos_encontrados[tipo] = encontrado

        return resultado

    def _filtrar_arquivos_validos(self, anexos: list[Path], resultado: ResultadoValidacao) -> list[Path]:
        validos: list[Path] = []
        for arquivo in anexos:
            if not arquivo.exists() or not arquivo.is_file():
                resultado.pendencias.append(f"Arquivo inexistente: {arquivo.name}")
                continue
            if arquivo.suffix.lower() not in self.FORMATOS_PERMITIDOS:
                resultado.pendencias.append(f"Formato não permitido: {arquivo.name}")
                continue
            if arquivo.stat().st_size == 0:
                resultado.pendencias.append(f"Arquivo vazio: {arquivo.name}")
                continue
            validos.append(arquivo)
        return validos

    @staticmethod
    def _localizar(anexos: list[Path], palavras_chave: tuple[str, ...]) -> Path | None:
        for arquivo in anexos:
            nome = arquivo.stem.lower().replace("-", "_").replace(" ", "_")
            if palavras_chave == ("rg", "cnh", "identidade", "documento"):
                if any(palavra in nome for palavra in palavras_chave):
                    return arquivo
            elif all(palavra in nome for palavra in palavras_chave):
                return arquivo
        return None
