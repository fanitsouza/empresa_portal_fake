from pathlib import Path

from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao, ResultadoValidacao


class GeradorResposta:
    """Gera a resposta que futuramente será enviada por SMTP."""

    def __init__(self, config: Configuracao) -> None:
        self.config = config

    def gerar(
        self,
        solicitacao: Solicitacao,
        validacao: ResultadoValidacao,
    ) -> Path:
        caminho = self.config.respostas / f"{solicitacao.protocolo}.txt"

        if validacao.completa:
            corpo = (
                f"Olá, {solicitacao.nome_cliente}.\n\n"
                f"Recebemos e validamos a documentação do protocolo "
                f"{solicitacao.protocolo}.\n"
                "A solicitação será encaminhada ao próximo setor.\n\n"
                "Atenciosamente,\n"
                "Portal Fake Soluções Digitais"
            )
        else:
            lista = "\n".join(f"- {item}" for item in validacao.pendencias)
            corpo = (
                f"Olá, {solicitacao.nome_cliente}.\n\n"
                f"Identificamos pendências na documentação do protocolo "
                f"{solicitacao.protocolo}:\n\n"
                f"{lista}\n\n"
                "Envie os itens corrigidos para que possamos continuar o processo.\n\n"
                "Atenciosamente,\n"
                "Portal Fake Soluções Digitais"
            )

        caminho.write_text(corpo, encoding="utf-8")
        return caminho
