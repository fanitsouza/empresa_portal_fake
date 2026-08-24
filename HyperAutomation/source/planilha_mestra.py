from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from extracao_pdf import CAMPOS_OBRIGATORIOS


NOME_ABA = "Dados extraidos"
COLUNAS_BASE = [
    "Arquivo",
    *CAMPOS_OBRIGATORIOS,
    "Sucesso",
    "Campos ausentes",
    "Erro",
    "Atualizado em",
]

COLUNAS_CADASTRO = [
    "Status Cadastro",
    "Motivo Erro Cadastro",
    "Data Cadastro",
]

COLUNAS_SAC = [
    "Status SAC",
    "Protocolo SAC",
    "Data Envio SAC",
]

COLUNAS_COMPLETAS = [
    *COLUNAS_BASE,
    *COLUNAS_CADASTRO,
    *COLUNAS_SAC,
]

COLUNAS = COLUNAS_BASE


def atualizar_planilha_mestra(
    resultados: list[dict[str, Any]], caminho_planilha: str | Path
) -> tuple[Path, int, int]:
    """Cria ou atualiza a planilha, evitando duplicidade por CPF ou arquivo."""
    caminho = Path(caminho_planilha)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    if caminho.exists():
        workbook = load_workbook(caminho)
        planilha = workbook[NOME_ABA] if NOME_ABA in workbook.sheetnames else workbook.active
        _validar_cabecalho(planilha)
    else:
        workbook = Workbook()
        planilha = workbook.active
        planilha.title = NOME_ABA
        planilha.append(COLUNAS_BASE)
        _formatar_planilha(planilha)

    linhas_existentes = _indexar_linhas(planilha)
    adicionados = 0
    atualizados = 0

    for resultado in resultados:
        valores = _resultado_para_linha(resultado)
        chave = _chave_resultado(resultado)
        numero_linha = linhas_existentes.get(chave)

        if numero_linha is None:
            planilha.append(valores)
            numero_linha = planilha.max_row
            linhas_existentes[chave] = numero_linha
            adicionados += 1
        else:
            for coluna, valor in enumerate(valores, start=1):
                planilha.cell(numero_linha, coluna, valor)
            atualizados += 1

    planilha.auto_filter.ref = planilha.dimensions
    planilha.freeze_panes = "A2"
    workbook.save(caminho)
    return caminho, adicionados, atualizados


def atualizar_status_cadastro_planilha(
    resultados_cadastro: list[dict[str, Any]], caminho_planilha: str | Path
) -> Path:
    """Atualiza as colunas de status de cadastro no Portal Fake na planilha mestra."""
    caminho = Path(caminho_planilha)
    if not caminho.exists():
        raise FileNotFoundError(f"Planilha mestra não encontrada: {caminho}")

    workbook = load_workbook(caminho)
    planilha = workbook[NOME_ABA] if NOME_ABA in workbook.sheetnames else workbook.active

    # Garante colunas de cadastro no cabeçalho
    cabecalho = [str(planilha.cell(1, col).value or "").strip() for col in range(1, planilha.max_column + 1)]
    
    col_map = {nome: idx + 1 for idx, nome in enumerate(cabecalho) if nome}
    
    for nova_col in COLUNAS_CADASTRO:
        if nova_col not in col_map:
            nova_pos = len(col_map) + 1
            planilha.cell(1, nova_pos, nova_col)
            col_map[nova_col] = nova_pos

    linhas_existentes = _indexar_linhas(planilha)

    for item in resultados_cadastro:
        cpf = item.get("cpf", "")
        cpf_norm = re.sub(r"\D", "", cpf)
        chave = f"cpf:{cpf_norm}"
        numero_linha = linhas_existentes.get(chave)

        if numero_linha:
            planilha.cell(numero_linha, col_map["Status Cadastro"], item.get("status_cadastro", "SUCESSO"))
            planilha.cell(numero_linha, col_map["Motivo Erro Cadastro"], item.get("motivo_erro") or "")
            planilha.cell(numero_linha, col_map["Data Cadastro"], item.get("data_cadastro") or datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    _formatar_planilha(planilha)
    workbook.save(caminho)
    return caminho


def atualizar_status_sac_planilha(
    resultados_sac: list[dict[str, Any]], caminho_planilha: str | Path
) -> Path:
    """Atualiza as colunas de status do SAC na planilha mestra."""
    caminho = Path(caminho_planilha)
    if not caminho.exists():
        raise FileNotFoundError(f"Planilha mestra não encontrada: {caminho}")

    workbook = load_workbook(caminho)
    planilha = workbook[NOME_ABA] if NOME_ABA in workbook.sheetnames else workbook.active

    cabecalho = [str(planilha.cell(1, col).value or "").strip() for col in range(1, planilha.max_column + 1)]
    col_map = {nome: idx + 1 for idx, nome in enumerate(cabecalho) if nome}

    for nova_col in COLUNAS_SAC:
        if nova_col not in col_map:
            nova_pos = len(col_map) + 1
            planilha.cell(1, nova_pos, nova_col)
            col_map[nova_col] = nova_pos

    linhas_existentes = _indexar_linhas(planilha)

    for item in resultados_sac:
        cpf = item.get("cpf", "")
        cpf_norm = re.sub(r"\D", "", cpf)
        chave = f"cpf:{cpf_norm}"
        numero_linha = linhas_existentes.get(chave)

        if numero_linha:
            planilha.cell(numero_linha, col_map["Status SAC"], item.get("status_sac", "NOTIFICADO"))
            planilha.cell(numero_linha, col_map["Protocolo SAC"], item.get("protocolo") or "")
            planilha.cell(numero_linha, col_map["Data Envio SAC"], item.get("data_envio") or datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    _formatar_planilha(planilha)
    workbook.save(caminho)
    return caminho


def carregar_registros_planilha(caminho_planilha: str | Path) -> list[dict[str, Any]]:
    """Lê todas as linhas da planilha mestra como dicionários estruturados."""
    caminho = Path(caminho_planilha)
    if not caminho.is_file():
        raise FileNotFoundError(f"Planilha mestra não encontrada: {caminho}")

    workbook = load_workbook(caminho, data_only=True)
    try:
        planilha = workbook[NOME_ABA] if NOME_ABA in workbook.sheetnames else workbook.active
        linhas = list(planilha.iter_rows(values_only=True))
        if not linhas:
            return []

        cabecalho = [str(c).strip() if c is not None else f"col_{idx}" for idx, c in enumerate(linhas[0])]
        registros = []

        for row in linhas[1:]:
            if not any(row):
                continue
            item = {}
            for idx, col_name in enumerate(cabecalho):
                valor = row[idx] if idx < len(row) else ""
                item[col_name] = "" if valor is None else str(valor).strip()
            registros.append(item)
        return registros
    finally:
        workbook.close()


def _resultado_para_linha(resultado: dict[str, Any]) -> list[Any]:
    dados = resultado.get("dados") or {}
    return [
        resultado.get("arquivo", ""),
        *(dados.get(campo, "") for campo in CAMPOS_OBRIGATORIOS),
        "Sim" if resultado.get("sucesso") else "Nao",
        ", ".join(resultado.get("campos_ausentes") or []),
        resultado.get("erro") or "",
        datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S"),
    ]


def _chave_resultado(resultado: dict[str, Any]) -> str:
    cpf = (resultado.get("dados") or {}).get("CPF", "")
    cpf_normalizado = re.sub(r"\D", "", cpf)
    if cpf_normalizado:
        return f"cpf:{cpf_normalizado}"
    return f"arquivo:{Path(resultado.get('arquivo', '')).resolve()}".casefold()


def _indexar_linhas(planilha) -> dict[str, int]:
    cabecalho = [str(planilha.cell(1, col).value or "").strip() for col in range(1, planilha.max_column + 1)]
    col_map = {nome: idx + 1 for idx, nome in enumerate(cabecalho) if nome}
    
    col_cpf = col_map.get("CPF", 3)
    col_arq = col_map.get("Arquivo", 1)

    linhas: dict[str, int] = {}
    for numero_linha in range(2, planilha.max_row + 1):
        cpf = str(planilha.cell(numero_linha, col_cpf).value or "")
        arquivo = str(planilha.cell(numero_linha, col_arq).value or "")
        cpf_normalizado = re.sub(r"\D", "", cpf)
        chave = (
            f"cpf:{cpf_normalizado}"
            if cpf_normalizado
            else f"arquivo:{Path(arquivo).resolve()}".casefold()
        )
        linhas[chave] = numero_linha
    return linhas


def _validar_cabecalho(planilha) -> None:
    cabecalho = [str(planilha.cell(1, coluna).value or "").strip() for coluna in range(1, len(COLUNAS_BASE) + 1)]
    for col_obrigatoria in ("Nome", "CPF", "E-mail"):
        if col_obrigatoria not in cabecalho:
            raise ValueError(
                f"Coluna obrigatória '{col_obrigatoria}' ausente na planilha mestra."
            )


def _formatar_planilha(planilha) -> None:
    preenchimento = PatternFill("solid", fgColor="1F4E78")
    for celula in planilha[1]:
        celula.font = Font(color="FFFFFF", bold=True)
        celula.fill = preenchimento

    larguras = {
        "A": 36,
        "B": 28,
        "C": 18,
        "D": 30,
        "E": 20,
        "F": 16,
        "G": 42,
        "H": 12,
        "I": 25,
        "J": 35,
        "K": 22,
        "L": 20,
        "M": 32,
        "N": 22,
        "O": 24,
        "P": 18,
        "Q": 22,
    }
    for col_idx in range(1, planilha.max_column + 1):
        col_letter = openpyxl.utils.get_column_letter(col_idx) if hasattr(openpyxl, "utils") else chr(64 + col_idx)
        if col_letter in larguras:
            planilha.column_dimensions[col_letter].width = larguras[col_letter]
