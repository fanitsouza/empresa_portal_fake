from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from processo_atendimento.gestor_arquivos import GestorArquivos
from processo_atendimento.validador_docs import ValidadorDocs
from processo_atendimento.resposta_cliente import RespostaClienteSMTP
from processo_atendimento.portal_integracao import PortalERPIntegracao
from processo_atendimento.orquestrador import OrquestradorProcessoAtendimento


class TestProcessoAtendimento(unittest.TestCase):

    def test_gestor_arquivos_estrutura(self) -> None:
        with TemporaryDirectory() as temp_dir:
            raiz = Path(temp_dir)
            gestor = GestorArquivos(raiz)
            pastas = gestor.garantir_estrutura_diretorios()
            self.assertTrue(pastas["downloads"].exists())
            self.assertTrue(pastas["documentos_ok"].exists())
            self.assertTrue(pastas["documentos_pendentes"].exists())
            self.assertTrue(pastas["encaminhados"].exists())

    def test_gestor_arquivos_movimentacao(self) -> None:
        with TemporaryDirectory() as temp_dir:
            raiz = Path(temp_dir)
            gestor = GestorArquivos(raiz)

            arq_teste = gestor.pasta_downloads / "teste_doc.pdf"
            arq_teste.write_text("conteudo teste", encoding="utf-8")

            dest_ok = gestor.mover_para_documentos_ok(arq_teste)
            self.assertFalse(arq_teste.exists())
            self.assertTrue(dest_ok.exists())
            self.assertEqual(dest_ok.parent, gestor.pasta_documentos_ok)

            dest_enc = gestor.mover_para_encaminhados(dest_ok)
            self.assertTrue(dest_enc.exists())
            self.assertEqual(dest_enc.parent, gestor.pasta_encaminhados)

    def test_validador_docs_aprovado(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "completo.pdf"
            pdf.write_text(
                "Ficha Cadastral Assinada\n"
                "Nome: Joao da Silva\n"
                "CPF: 123.456.789-00\n"
                "E-mail: joao@exemplo.com\n"
                "Documento Oficial com Foto RG 12345\n"
                "Comprovante de Residência Conta de Agua\n",
                encoding="utf-8",
            )
            validador = ValidadorDocs()
            aprovado, pendencias, dados = validador.validar_documentos_pdf(pdf)
            self.assertTrue(aprovado)
            self.assertEqual(len(pendencias), 0)
            self.assertEqual(dados["cpf"], "12345678900")

    def test_validador_docs_pendente(self) -> None:
        with TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "incompleto.pdf"
            pdf.write_text("Ficha Cadastral Assinada\nNome: Maria\n", encoding="utf-8")
            validador = ValidadorDocs()
            aprovado, pendencias, dados = validador.validar_documentos_pdf(pdf)
            self.assertFalse(aprovado)
            self.assertIn("Documento Oficial com Foto", pendencias)
            self.assertIn("Comprovante de Residência", pendencias)

    def test_orquestrador_fluxo_completo(self) -> None:
        with TemporaryDirectory() as temp_dir:
            raiz = Path(temp_dir)
            orquestrador = OrquestradorProcessoAtendimento(raiz)
            processados = orquestrador.executar_fluxo(modo="simulacao", headless=True)
            self.assertEqual(processados, 1)  # 1 aprovado, 1 pendente


if __name__ == "__main__":
    unittest.main()
