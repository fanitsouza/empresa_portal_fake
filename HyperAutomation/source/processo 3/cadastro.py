from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright


PATH_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = PATH_ROOT / "resources" / "portal_fake" / "index.html"
PLANILHA_PADRAO = PATH_ROOT / "resources" / "planilha_mestra.xlsx"
BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data"
PASTA_SCREENSHOTS = PATH_ROOT / "resources" / "screenshots"
NOME_ABA = "Dados extraidos"


def carregar_usuarios(caminho_planilha: str | Path) -> list[dict[str, str]]:
    """Carrega da planilha mestra os registros extraidos com sucesso."""
    caminho = Path(caminho_planilha).expanduser().resolve()
    if not caminho.is_file():
        raise FileNotFoundError(f"Planilha mestra nao encontrada: {caminho}")
    if caminho.suffix.lower() != ".xlsx":
        raise ValueError(f"A planilha deve possuir extensao .xlsx: {caminho}")

    workbook = load_workbook(caminho, read_only=True, data_only=True)
    try:
        planilha = workbook[NOME_ABA] if NOME_ABA in workbook.sheetnames else workbook.active
        linhas = planilha.iter_rows(values_only=True)
        cabecalho = next(linhas, None)
        if not cabecalho:
            return []

        colunas = {
            str(nome).strip(): indice
            for indice, nome in enumerate(cabecalho)
            if nome is not None
        }
        obrigatorias = {"Nome", "CPF", "E-mail", "Telefone", "Nascimento", "Endereco"}
        ausentes = sorted(obrigatorias - colunas.keys())
        if ausentes:
            raise ValueError(
                "Colunas obrigatorias ausentes na planilha: " + ", ".join(ausentes)
            )

        usuarios: list[dict[str, str]] = []
        for numero_linha, linha in enumerate(linhas, start=2):
            registro = {
                nome: _texto(linha[indice]) if indice < len(linha) else ""
                for nome, indice in colunas.items()
            }
            if not _registro_aprovado(registro):
                continue

            nome, sobrenome = _separar_nome(registro["Nome"])
            usuarios.append(
                {
                    "nome": nome,
                    "sobrenome": sobrenome,
                    "cpf": _normalizar_cpf(registro["CPF"], numero_linha),
                    "email": registro["E-mail"],
                    "telefone": registro["Telefone"],
                    "nascimento": _formatar_nascimento(
                        linha[colunas["Nascimento"]]
                    ),
                    "endereco": registro["Endereco"],
                    "observacao": "Cadastro importado da planilha mestra",
                    "status": "ATIVO",
                }
            )
        return usuarios
    finally:
        workbook.close()


def _registro_aprovado(registro: dict[str, str]) -> bool:
    sucesso = registro.get("Sucesso", "Sim").strip().casefold()
    return sucesso in {"sim", "true", "1", "sucesso"}


def _separar_nome(nome_completo: str) -> tuple[str, str]:
    partes = nome_completo.strip().split(maxsplit=1)
    if not partes:
        return "", ""
    return partes[0], partes[1] if len(partes) == 2 else ""


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _normalizar_cpf(valor: Any, numero_linha: int | None = None) -> str:
    """Remove a pontuacao e garante os 11 digitos exigidos pelo portal."""
    cpf = re.sub(r"\D", "", _texto(valor))
    if len(cpf) != 11:
        local = f" na linha {numero_linha}" if numero_linha is not None else ""
        raise ValueError(f"CPF invalido{local}: deve conter exatamente 11 digitos.")
    return cpf


def _formatar_nascimento(valor: Any) -> str:
    """Converte a data para AAAA-MM-DD, formato aceito pelo input HTML date."""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")

    texto = _texto(valor)
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return texto


def preencher_portal_rapido(page, usuarios: list[dict[str, str]], qtd: int = 10) -> None:
    """Preenche o Portal Fake com os usuarios carregados da planilha mestra."""
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("#btnClearAll")

    lista = usuarios[:qtd] if qtd else usuarios
    total = len(lista)
    print(f"[RPA Preenchimento] Cadastrando {total} usuarios no Portal Fake...")

    for usuario in lista:
        page.click("#btnNovo")
        page.fill("#f_nome", usuario.get("nome", ""))
        page.fill("#f_sobrenome", usuario.get("sobrenome", ""))
        cpf = _normalizar_cpf(usuario.get("cpf", ""))
        page.fill("#f_cpf", cpf)
        cpf_preenchido = page.locator("#f_cpf").input_value()
        if cpf_preenchido != cpf:
            raise RuntimeError(
                f"Falha ao preencher o CPF. Esperado: {cpf}; preenchido: {cpf_preenchido}."
            )
        page.fill("#f_email", usuario.get("email", ""))
        page.fill("#f_telefone", usuario.get("telefone", ""))
        page.fill("#f_nascimento", usuario.get("nascimento", ""))
        page.fill("#f_endereco", usuario.get("endereco", ""))
        page.fill("#f_observacao", usuario.get("observacao", ""))
        page.select_option("#f_status", (usuario.get("status") or "ATIVO").upper())
        page.click("#btnSalvar")

    print(f"[RPA Preenchimento] Sucesso! {total} cadastros inseridos no portal.")


def salvar_evidencia_cadastros(page, pasta_destino: str | Path) -> Path:
    """Salva uma captura de tela completa do portal após os cadastros."""
    pasta = Path(pasta_destino).expanduser().resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    caminho = pasta / f"cadastros_concluidos_{data_hora}.png"

    page.wait_for_timeout(500)
    page.screenshot(path=str(caminho), full_page=True)
    print(f"[Evidencia] Screenshot dos cadastros salvo em: {caminho}")
    return caminho


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cadastra no Portal Fake os dados da planilha mestra."
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        default=str(PLANILHA_PADRAO),
        help="Caminho do arquivo .xlsx (padrao: resources/planilha_mestra.xlsx).",
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=0,
        help="Quantidade maxima de cadastros. Use 0 para cadastrar todos.",
    )
    parser.add_argument(
        "--pasta-screenshots",
        default=str(PASTA_SCREENSHOTS),
        help="Pasta onde a evidencia final em PNG sera salva.",
    )
    return parser


def main() -> int:
    argumentos = criar_parser().parse_args()
    usuarios = carregar_usuarios(argumentos.planilha)
    if not usuarios:
        print("Nenhum registro com sucesso encontrado na planilha mestra.")
        return 1

    if not INDEX_HTML.is_file():
        raise FileNotFoundError(f"Portal Fake nao encontrado: {INDEX_HTML}")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
        )
        try:
            page = context.new_page()
            page.goto(INDEX_HTML.resolve().as_uri())
            preencher_portal_rapido(page, usuarios, qtd=argumentos.quantidade)
            salvar_evidencia_cadastros(page, argumentos.pasta_screenshots)
        finally:
            context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
