from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class StatusSolicitacao(str, Enum):
    APROVADA = "DOCUMENTACAO_APROVADA"
    PENDENTE = "DOCUMENTACAO_PENDENTE"
    ERRO = "ERRO_PROCESSAMENTO"


@dataclass(frozen=True)
class Solicitacao:
    protocolo: str
    nome_cliente: str
    email_cliente: str
    cpf: str
    anexos: list[Path]


@dataclass
class ResultadoValidacao:
    documentos_encontrados: dict[str, Path] = field(default_factory=dict)
    pendencias: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.pendencias


@dataclass(frozen=True)
class ResultadoProcessamento:
    protocolo: str
    status: StatusSolicitacao
    pendencias: list[str]
    pasta_destino: Path
    arquivo_resposta: Path
    arquivo_registro: Path
