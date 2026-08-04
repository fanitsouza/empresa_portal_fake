import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "source"))

from localizador_documentos import (  # noqa: E402
    ConfiguracaoIMAP,
    baixar_pdfs_aprovados_por_imap,
    localizar_pdfs_aprovados,
)


def test_localizacao_recursiva_de_pdfs(tmp_path):
    pasta = tmp_path / "Documentos_Aprovados"
    subpasta = pasta / "sub"
    subpasta.mkdir(parents=True)
    pdf_raiz = pasta / "raiz.pdf"
    pdf_subpasta = subpasta / "sub.pdf"
    pdf_raiz.write_bytes(b"%PDF")
    pdf_subpasta.write_bytes(b"%PDF")
    (subpasta / "ignorar.txt").write_text("x", encoding="utf-8")

    encontrados = localizar_pdfs_aprovados(pasta)

    assert encontrados == sorted([pdf_raiz, pdf_subpasta])


def test_mock_imap_baixa_anexos_pdf_sem_sobrescrever(tmp_path):
    destino = tmp_path / "Documentos_Aprovados"
    destino.mkdir()
    (destino / "cadastro.pdf").write_bytes(b"existente")

    mensagem = EmailMessage()
    mensagem["Subject"] = "Cadastro aprovado"
    mensagem["From"] = "cliente@exemplo.com"
    mensagem["To"] = "bot@exemplo.com"
    mensagem.set_content("Documento aprovado para processamento.")
    mensagem.add_attachment(
        b"%PDF conteudo",
        maintype="application",
        subtype="pdf",
        filename="cadastro.pdf",
    )
    mensagem.add_attachment(
        b"texto",
        maintype="text",
        subtype="plain",
        filename="ignorar.txt",
    )

    class FakeIMAP:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def login(self, user, password):
            return "OK", [b""]

        def select(self, mailbox):
            return "OK", [b""]

        def search(self, charset, criterion):
            return "OK", [b"1"]

        def fetch(self, message_id, query):
            return "OK", [(b"1", mensagem.as_bytes())]

        def logout(self):
            return "OK", [b""]

    config = ConfiguracaoIMAP(
        remetente="bot@exemplo.com",
        senha="senha",
        palavra_aprovado="aprovado",
    )

    resultado = baixar_pdfs_aprovados_por_imap(destino, config, FakeIMAP)

    assert resultado.emails_analisados == 1
    assert resultado.pdfs_baixados == 1
    assert resultado.arquivos == [destino / "cadastro_1.pdf"]
    assert (destino / "cadastro.pdf").read_bytes() == b"existente"
    assert (destino / "cadastro_1.pdf").read_bytes() == b"%PDF conteudo"

