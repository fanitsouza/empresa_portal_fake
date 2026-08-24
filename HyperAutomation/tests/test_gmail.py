import unittest
from pathlib import Path
from atendimento.gmail_recebimento import nome_seguro, caminho_unico, dados_download_url


class TestGmailRecebimentoHelpers(unittest.TestCase):
    def test_nome_seguro(self) -> None:
        self.assertEqual(nome_seguro("doc @#$ 1.pdf"), "doc _ 1.pdf")
        self.assertEqual(nome_seguro(""), "anexo")

    def test_candidato_caminho_unico(self) -> None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp_dir:
            pasta = Path(temp_dir)
            f1 = pasta / "documento.pdf"
            f1.write_text("teste")
            candidato = caminho_unico(pasta, "documento.pdf")
            self.assertEqual(candidato.name, "documento_2.pdf")

    def test_dados_download_url(self) -> None:
        val = "1:arquivo%20teste.pdf:https://example.com/download"
        res = dados_download_url(val)
        self.assertIsNotNone(res)
        if res:
            self.assertEqual(res[0], "arquivo teste.pdf")
            self.assertEqual(res[1], "https://example.com/download")



if __name__ == "__main__":
    unittest.main()
