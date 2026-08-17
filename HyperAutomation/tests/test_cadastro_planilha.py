import importlib.util
from pathlib import Path

import pytest
from openpyxl import Workbook


CAMINHO_MODULO = Path(__file__).resolve().parents[1] / "source" / "processo 3" / "cadastro.py"
SPEC = importlib.util.spec_from_file_location("cadastro_processo_3", CAMINHO_MODULO)
cadastro = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cadastro)


def criar_planilha(caminho: Path) -> None:
    workbook = Workbook()
    planilha = workbook.active
    planilha.title = "Dados extraidos"
    planilha.append(
        ["Arquivo", "Nome", "CPF", "E-mail", "Telefone", "Nascimento", "Endereco", "Sucesso"]
    )
    planilha.append(
        ["ana.pdf", "Ana Maria Silva", "123.456.789-01", "ana@email.com", "92999999999", "01/01/2000", "Rua A", "Sim"]
    )
    planilha.append(["erro.pdf", "Pessoa Invalida", "", "", "", "", "", "Nao"])
    workbook.save(caminho)


def test_carrega_planilha_mestra_recebida_por_path(tmp_path):
    caminho = tmp_path / "mestra.xlsx"
    criar_planilha(caminho)

    usuarios = cadastro.carregar_usuarios(caminho)

    assert len(usuarios) == 1
    assert usuarios[0]["nome"] == "Ana"
    assert usuarios[0]["sobrenome"] == "Maria Silva"
    assert usuarios[0]["cpf"] == "12345678901"
    assert usuarios[0]["nascimento"] == "2000-01-01"


def test_rejeita_arquivo_que_nao_e_xlsx(tmp_path):
    caminho = tmp_path / "mestra.csv"
    caminho.write_text("Nome,CPF", encoding="utf-8")

    with pytest.raises(ValueError, match="extensao .xlsx"):
        cadastro.carregar_usuarios(caminho)


def test_salva_screenshot_final_em_pasta_configurada(tmp_path):
    class PaginaFake:
        def __init__(self):
            self.timeout = None
            self.screenshot_args = None

        def wait_for_timeout(self, timeout):
            self.timeout = timeout

        def screenshot(self, **kwargs):
            self.screenshot_args = kwargs
            Path(kwargs["path"]).write_bytes(b"png")

    pagina = PaginaFake()

    caminho = cadastro.salvar_evidencia_cadastros(pagina, tmp_path / "evidencias")

    assert caminho.is_file()
    assert caminho.name.startswith("cadastros_concluidos_")
    assert caminho.suffix == ".png"
    assert pagina.timeout == 500
    assert pagina.screenshot_args["full_page"] is True


def test_normaliza_cpf_formatado_para_os_11_digitos():
    assert cadastro._normalizar_cpf("123.456.789-01") == "12345678901"


def test_rejeita_cpf_incompleto():
    with pytest.raises(ValueError, match="exatamente 11 digitos"):
        cadastro._normalizar_cpf("123.456")
