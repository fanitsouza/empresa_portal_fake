from pathlib import Path
import shutil
from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao, ResultadoValidacao


class ClassificadorArquivos:
    """Copia os documentos para a pasta correspondente ao resultado."""

    def __init__(self, config: Configuracao) -> None:
        self.config = config

    def classificar(self, solicitacao: Solicitacao, validacao: ResultadoValidacao) -> Path:
        base = self.config.documentos_ok if validacao.completa else self.config.documentos_pendentes
        destino = base / solicitacao.protocolo
        destino.mkdir(parents=True, exist_ok=True)

        for anexo in solicitacao.anexos:
            if anexo.exists() and anexo.is_file():
                shutil.copy2(anexo, destino / anexo.name)
        return destino
