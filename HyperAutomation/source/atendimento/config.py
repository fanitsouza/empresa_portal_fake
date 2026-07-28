from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Configuracao:
    """Centraliza os diretÃ³rios utilizados pela automaÃ§Ã£o."""

    raiz: Path
    caixa_entrada: Path
    downloads: Path
    documentos_ok: Path
    documentos_pendentes: Path
    encaminhados: Path
    respostas: Path
    registros: Path

    @classmethod
    def criar(cls, raiz: Path | None = None) -> "Configuracao":
        raiz_projeto = raiz or Path(__file__).resolve().parents[2]
        erp = raiz_projeto / "resources" / "ERP_Portal_Fake"

        config = cls(
            raiz=raiz_projeto,
            caixa_entrada=erp / "Caixa_Entrada",
            downloads=erp / "Downloads",
            documentos_ok=erp / "Documentos_OK",
            documentos_pendentes=erp / "Documentos_Pendentes",
            encaminhados=erp / "Encaminhados",
            respostas=erp / "Respostas",
            registros=erp / "Registros",
        )

        for pasta in (
            config.caixa_entrada,
            config.downloads,
            config.documentos_ok,
            config.documentos_pendentes,
            config.encaminhados,
            config.respostas,
            config.registros,
        ):
            pasta.mkdir(parents=True, exist_ok=True)

        return config

