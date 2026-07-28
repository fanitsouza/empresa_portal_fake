from datetime import datetime, timezone
from pathlib import Path
import json
from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao, ResultadoValidacao, StatusSolicitacao


class RegistradorProcessamento:
    """Mantém rastreabilidade da execução em um arquivo JSON."""

    def __init__(self, config: Configuracao) -> None:
        self.config = config

    def registrar(self, solicitacao: Solicitacao, validacao: ResultadoValidacao, status: StatusSolicitacao, pasta_destino: Path, arquivo_resposta: Path) -> Path:
        caminho = self.config.registros / f"{solicitacao.protocolo}.json"
        dados = {
            "protocolo": solicitacao.protocolo,
            "cliente": {
                "nome": solicitacao.nome_cliente,
                "email": solicitacao.email_cliente,
                "cpf": solicitacao.cpf,
            },
            "status": status.value,
            "documentos_encontrados": {chave: str(valor) for chave, valor in validacao.documentos_encontrados.items()},
            "pendencias": validacao.pendencias,
            "pasta_destino": str(pasta_destino),
            "arquivo_resposta": str(arquivo_resposta),
            "processado_em_utc": datetime.now(timezone.utc).isoformat(),
        }
        caminho.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        return caminho
