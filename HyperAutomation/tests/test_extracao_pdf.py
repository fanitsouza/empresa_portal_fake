import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "source"))

from extracao_pdf import (  # noqa: E402
    CAMPOS_OBRIGATORIOS,
    PDFSemTextoPesquisavelError,
    extrair_campos_texto,
    extrair_texto_pdf,
    processar_pdfs,
    salvar_resultados_json,
)


def test_extracao_de_todos_os_campos_mesma_linha():
    texto = """
    Nome completo: Maria Souza
    CPF: 12345678901
    E-mail: MARIA@EXEMPLO.COM
    Celular: 92999998888
    Data de nascimento: 2000-01-31
    Endereco completo: Rua A, 10 - Manaus/AM
    """

    dados = extrair_campos_texto(texto)

    assert dados == {
        "Nome": "Maria Souza",
        "CPF": "123.456.789-01",
        "E-mail": "maria@exemplo.com",
        "Telefone": "(92) 99999-8888",
        "Nascimento": "31/01/2000",
        "Endereco": "Rua A, 10 - Manaus/AM",
    }


def test_extracao_de_campos_na_linha_seguinte():
    texto = """
    Nome:
    Joao Lima
    CPF:
    123.456.789-01
    Email:
    joao@exemplo.com
    Telefone:
    (92) 98888-7777
    Nascimento:
    01/02/1999
    Endereço:
    Avenida Brasil, 200
    """

    dados = extrair_campos_texto(texto)

    assert dados["Nome"] == "Joao Lima"
    assert dados["CPF"] == "123.456.789-01"
    assert dados["E-mail"] == "joao@exemplo.com"
    assert dados["Telefone"] == "(92) 98888-7777"
    assert dados["Nascimento"] == "01/02/1999"
    assert dados["Endereco"] == "Avenida Brasil, 200"


def test_cpf_com_e_sem_formatacao():
    assert extrair_campos_texto("CPF: 12345678901")["CPF"] == "123.456.789-01"
    assert extrair_campos_texto("CPF: 123.456.789-01")["CPF"] == "123.456.789-01"


def test_variacoes_email_e_endereco():
    texto = """
    Email: pessoa@exemplo.com
    Endereco: Rua Sem Acento
    """

    dados = extrair_campos_texto(texto)

    assert dados["E-mail"] == "pessoa@exemplo.com"
    assert dados["Endereco"] == "Rua Sem Acento"


def test_campos_obrigatorios_ausentes(tmp_path, monkeypatch):
    pdf = tmp_path / "incompleto.pdf"
    pdf.write_bytes(b"%PDF fake")
    monkeypatch.setattr(
        "extracao_pdf.extrair_texto_pdf",
        lambda _: "Nome: Ana\nCPF: 12345678901\nNascimento: 01/01/2000",
    )

    resultado = processar_pdfs([pdf])[0]

    assert resultado["sucesso"] is False
    assert resultado["dados"]["Nome"] == "Ana"
    assert resultado["campos_ausentes"] == ["E-mail", "Telefone", "Endereco"]
    assert "Campos obrigatorios nao encontrados" in resultado["erro"]


def test_pdf_inexistente_retorna_erro_controlado(tmp_path):
    resultado = processar_pdfs([tmp_path / "ausente.pdf"])[0]

    assert resultado["sucesso"] is False
    assert resultado["dados"] == {}
    assert resultado["campos_ausentes"] == CAMPOS_OBRIGATORIOS
    assert "Arquivo inexistente" in resultado["erro"]


def test_arquivo_que_nao_seja_pdf_retorna_erro(tmp_path):
    arquivo = tmp_path / "dados.txt"
    arquivo.write_text("Nome: Ana", encoding="utf-8")

    resultado = processar_pdfs([arquivo])[0]

    assert resultado["sucesso"] is False
    assert "extensao .pdf" in resultado["erro"]


def test_pdf_sem_texto_pesquisavel(tmp_path):
    from pypdf import PdfWriter

    pdf = tmp_path / "sem_texto.pdf"
    escritor = PdfWriter()
    escritor.add_blank_page(width=72, height=72)
    with pdf.open("wb") as arquivo:
        escritor.write(arquivo)

    with pytest.raises(PDFSemTextoPesquisavelError):
        extrair_texto_pdf(pdf)

    resultado = processar_pdfs([pdf])[0]
    assert resultado["sucesso"] is False
    assert "OCR" in resultado["erro"]


def test_erro_controlado_nao_interrompe_demais_pdfs(tmp_path, monkeypatch):
    primeiro = tmp_path / "primeiro.pdf"
    segundo = tmp_path / "segundo.pdf"
    primeiro.write_bytes(b"%PDF fake")
    segundo.write_bytes(b"%PDF fake")

    def fake_extrair(caminho):
        if Path(caminho).name == "primeiro.pdf":
            raise PDFSemTextoPesquisavelError(
                "O PDF nao possui texto pesquisavel e pode exigir OCR."
            )
        return """
        Nome: Ana
        CPF: 12345678901
        E-mail: ana@exemplo.com
        Telefone: 92999998888
        Nascimento: 01/01/2000
        Endereco: Rua A
        """

    monkeypatch.setattr("extracao_pdf.extrair_texto_pdf", fake_extrair)

    resultados = processar_pdfs([primeiro, segundo])

    assert resultados[0]["sucesso"] is False
    assert resultados[1]["sucesso"] is True


def test_geracao_correta_do_json(tmp_path):
    saida = tmp_path / "saida" / "resultado.json"
    resultados = [
        {
            "arquivo": "arquivo.pdf",
            "sucesso": True,
            "dados": {"Nome": "Ana"},
            "campos_ausentes": [],
            "erro": None,
        }
    ]

    caminho = salvar_resultados_json(resultados, saida)

    assert caminho == saida
    assert json.loads(saida.read_text(encoding="utf-8")) == resultados

