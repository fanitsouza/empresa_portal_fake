import logging
import shutil
from pathlib import Path

# Configuração de Logger com prefixo corporativo
logger = logging.getLogger("GESTOR_ARQUIVOS")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")


class GestorArquivos:
    """Gerencia a estrutura de diretórios do ERP Simulado e a movimentação de arquivos."""

    def __init__(self, raiz_projeto: Path | None = None) -> None:
        if raiz_projeto is None:
            # Sobe 3 níveis a partir deste arquivo (source/processo_atendimento/gestor_arquivos.py) -> HyperAutomation
            raiz_projeto = Path(__file__).resolve().parents[2]

        self.raiz_erp = raiz_projeto / "resources" / "ERP_Portal_Fake"
        self.pasta_downloads = self.raiz_erp / "Downloads"
        self.pasta_documentos_ok = self.raiz_erp / "Documentos_OK"
        self.pasta_documentos_pendentes = self.raiz_erp / "Documentos_Pendentes"
        self.pasta_encaminhados = self.raiz_erp / "Encaminhados"

        self.garantir_estrutura_diretorios()

    def garantir_estrutura_diretorios(self) -> dict[str, Path]:
        """Garante a criação dinâmica dos diretórios necessários caso não existam."""
        pastas = {
            "downloads": self.pasta_downloads,
            "documentos_ok": self.pasta_documentos_ok,
            "documentos_pendentes": self.pasta_documentos_pendentes,
            "encaminhados": self.pasta_encaminhados,
        }

        for nome, pasta in pastas.items():
            if not pasta.exists():
                pasta.mkdir(parents=True, exist_ok=True)
                logger.info(f"[GESTOR ARQUIVOS] Diretório criado: {pasta}")
            else:
                logger.debug(f"[GESTOR ARQUIVOS] Diretório existente: {pasta}")

        return pastas

    def _mover_arquivo(self, arquivo_origem: Path, pasta_destino: Path) -> Path:
        """Move um arquivo para a pasta destino com shutil.move garantindo integridade."""
        if not arquivo_origem.exists() or not arquivo_origem.is_file():
            logger.error(f"[GESTOR ARQUIVOS] Arquivo não encontrado para movimentação: {arquivo_origem}")
            raise FileNotFoundError(f"Arquivo não existe: {arquivo_origem}")

        pasta_destino.mkdir(parents=True, exist_ok=True)
        caminho_destino = pasta_destino / arquivo_origem.name

        # Se já existir arquivo com mesmo nome no destino, substitui
        if caminho_destino.exists():
            caminho_destino.unlink()

        destino_final = shutil.move(str(arquivo_origem), str(caminho_destino))
        logger.info(f"[GESTOR ARQUIVOS] Arquivo movido: {arquivo_origem.name} -> {pasta_destino.name}")
        return Path(destino_final)

    def mover_para_downloads(self, arquivo_origem: Path) -> Path:
        """Move um arquivo baixado para a pasta Downloads/."""
        return self._mover_arquivo(arquivo_origem, self.pasta_downloads)

    def mover_para_documentos_ok(self, arquivo_origem: Path) -> Path:
        """Move um arquivo aprovado para Documentos_OK/."""
        return self._mover_arquivo(arquivo_origem, self.pasta_documentos_ok)

    def mover_para_documentos_pendentes(self, arquivo_origem: Path) -> Path:
        """Move um arquivo com pendências para Documentos_Pendentes/."""
        return self._mover_arquivo(arquivo_origem, self.pasta_documentos_pendentes)

    def mover_para_encaminhados(self, arquivo_origem: Path) -> Path:
        """Move um arquivo de cadastro ativado no ERP para Encaminhados/."""
        return self._mover_arquivo(arquivo_origem, self.pasta_encaminhados)
