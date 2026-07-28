from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from atendimento.validador import ValidadorDocumentos


class TestValidadorDocumentos(unittest.TestCase):
    def setUp(self) -> None:
        self.validador = ValidadorDocumentos()

    def criar_arquivo(self, pasta: Path, nome: str) -> Path:
        caminho = pasta / nome
        caminho.write_bytes(b"arquivo de teste")
        return caminho

    def test_documentacao_completa(self) -> None:
        with TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            anexos = [
                self.criar_arquivo(pasta, "ficha_cadastro.pdf"),
                self.criar_arquivo(pasta, "rg.jpg"),
                self.criar_arquivo(pasta, "comprovante_residencia.pdf"),
            ]
            resultado = self.validador.validar(anexos)
            self.assertTrue(resultado.completa)
            self.assertEqual([], resultado.pendencias)
            self.assertEqual(3, len(resultado.documentos_encontrados))

    def test_documentacao_pendente(self) -> None:
        with TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            anexos = [
                self.criar_arquivo(pasta, "ficha_cadastro.pdf"),
                self.criar_arquivo(pasta, "rg.jpg"),
            ]
            resultado = self.validador.validar(anexos)
            self.assertFalse(resultado.completa)
            self.assertIn("Ausente: Comprovante de residência", resultado.pendencias)

    def test_rejeita_formato_nao_permitido(self) -> None:
        with TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            anexos = [
                self.criar_arquivo(pasta, "ficha_cadastro.exe"),
                self.criar_arquivo(pasta, "rg.jpg"),
                self.criar_arquivo(pasta, "comprovante_residencia.pdf"),
            ]
            resultado = self.validador.validar(anexos)
            self.assertFalse(resultado.completa)
            self.assertTrue(any("Formato não permitido" in item for item in resultado.pendencias))


if __name__ == "__main__":
    unittest.main()
