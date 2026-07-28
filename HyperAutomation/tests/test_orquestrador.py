from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao, StatusSolicitacao
from atendimento.orquestrador import OrquestradorAtendimento


class TestOrquestradorAtendimento(unittest.TestCase):
    def criar_arquivo(self, pasta: Path, nome: str) -> Path:
        caminho = pasta / nome
        caminho.write_bytes(b"arquivo de teste")
        return caminho

    def test_processa_solicitacao_aprovada(self) -> None:
        with TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            config = Configuracao.criar(raiz)
            origem = raiz / "origem"
            origem.mkdir()
            solicitacao = Solicitacao(
                protocolo="TESTE-001",
                nome_cliente="Cliente Teste",
                email_cliente="cliente@example.com",
                cpf="12345678900",
                anexos=[
                    self.criar_arquivo(origem, "ficha_cadastro.pdf"),
                    self.criar_arquivo(origem, "cnh.png"),
                    self.criar_arquivo(origem, "comprovante_residencia.pdf"),
                ],
            )
            resultado = OrquestradorAtendimento(config).processar(solicitacao)
            self.assertEqual(StatusSolicitacao.APROVADA, resultado.status)
            self.assertTrue(resultado.pasta_destino.exists())
            self.assertTrue(resultado.arquivo_resposta.exists())
            self.assertTrue(resultado.arquivo_registro.exists())


if __name__ == "__main__":
    unittest.main()
