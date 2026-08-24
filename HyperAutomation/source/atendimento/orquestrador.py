from atendimento.classificador import ClassificadorArquivos
from atendimento.config import Configuracao
from atendimento.modelos import ResultadoProcessamento, Solicitacao, StatusSolicitacao
from atendimento.registro import RegistradorProcessamento
from atendimento.resposta import GeradorResposta
from atendimento.validador import ValidadorDocumentos


class OrquestradorAtendimento:
    """Executa o fluxo completo do núcleo do Processo 1."""

    def __init__(self, config: Configuracao) -> None:
        self.validador = ValidadorDocumentos()
        self.classificador = ClassificadorArquivos(config)
        self.gerador_resposta = GeradorResposta(config)
        self.registrador = RegistradorProcessamento(config)

    def processar(self, solicitacao: Solicitacao) -> ResultadoProcessamento:
        validacao = self.validador.validar(solicitacao.anexos)
        pasta_destino = self.classificador.classificar(solicitacao, validacao)
        arquivo_resposta = self.gerador_resposta.gerar(solicitacao, validacao)
        status = StatusSolicitacao.APROVADA if validacao.completa else StatusSolicitacao.PENDENTE
        arquivo_registro = self.registrador.registrar(
            solicitacao, validacao, status, pasta_destino, arquivo_resposta
        )
        return ResultadoProcessamento(
            protocolo=solicitacao.protocolo,
            status=status,
            pendencias=list(validacao.pendencias),
            pasta_destino=pasta_destino,
            arquivo_resposta=arquivo_resposta,
            arquivo_registro=arquivo_registro,
        )
