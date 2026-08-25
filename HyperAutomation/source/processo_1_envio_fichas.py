"""
Processo 1 - Envio de Fichas para Assinatura
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Ler os dados cadastrais diretamente do arquivo CSV (resources/cadastros_portal_fake_20.csv).
2. Selecionar o registro do cliente a partir do parâmetro fornecido (linha, ID de solicitação, CPF, nome ou 'todos').
3. Gerar a Ficha de Cadastro preenchida (.docx) para o registro selecionado.
4. Disparar e-mail com a ficha em anexo para o cliente assinar.
(Obs: O cadastro no Portal Fake é realizado exclusivamente no Setor de Cadastro - Processo 3, a partir da Planilha Mestra).
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"
CSV_PATH = RESOURCES_DIR / "cadastros_portal_fake_20.csv"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

from documento_email import criar_documento, enviar_email

LOGGER = logging.getLogger("PROCESSO_1_ENVIO")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(name)s] %(levelname)s: %(message)s")


def carregar_usuarios(csv_path: Path = CSV_PATH) -> List[Dict[str, Any]]:
    """Carrega todos os registros cadastrais do arquivo CSV."""
    if not csv_path.exists():
        LOGGER.error(f"Arquivo CSV não encontrado em: {csv_path}")
        return []
    
    usuarios: List[Dict[str, Any]] = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            usuarios.append(row)
    return usuarios


def formatar_cliente_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Padroniza chaves de cliente com suporte a nomes em maiúsculas e minúsculas."""
    return {
        "id_solicitacao": str(raw.get("id_solicitacao") or raw.get("id") or ""),
        "Nome": str(raw.get("Nome") or raw.get("nome") or ""),
        "Sobrenome": str(raw.get("Sobrenome") or raw.get("sobrenome") or ""),
        "CPF": str(raw.get("CPF") or raw.get("cpf") or ""),
        "E-mail": str(raw.get("E-mail") or raw.get("email") or ""),
        "Telefone": str(raw.get("Telefone") or raw.get("telefone") or ""),
        "Nascimento": str(raw.get("Nascimento") or raw.get("nascimento") or ""),
        "Endereco": str(raw.get("Endereco") or raw.get("endereco") or ""),
        "Status": str(raw.get("Status") or raw.get("status") or "ATIVO"),
        "Observacao": str(raw.get("Observacao") or raw.get("observacao") or ""),
    }


def selecionar_cliente_csv(
    usuarios: List[Dict[str, Any]], registro: Any
) -> Tuple[int, Dict[str, Any]]:
    """
    Localiza o cliente desejado na lista do CSV com base em:
    - Índice da linha (0, 1, 2...)
    - ID da solicitação (1, 2, 3...)
    - CPF (com ou sem pontuação)
    - Nome ou Sobrenome do cliente
    """
    if not usuarios:
        raise ValueError("A lista de usuários do CSV está vazia.")

    # Se nenhum parâmetro foi passado, seleciona o primeiro registro (índice 0)
    if registro is None or str(registro).strip() == "":
        return 0, formatar_cliente_dict(usuarios[0])

    reg_str = str(registro).strip()

    # 1. Tentativa como número inteiro (índice ou ID)
    if reg_str.isdigit():
        val = int(reg_str)
        # Se for um índice direto válido na lista (0 <= val < len)
        if 0 <= val < len(usuarios):
            return val, formatar_cliente_dict(usuarios[val])

        # Se for um ID de solicitação (ex: 1 a 20)
        for idx, u in enumerate(usuarios):
            if str(u.get("id_solicitacao") or "").strip() == reg_str:
                return idx, formatar_cliente_dict(u)

    # 2. Tentativa por CPF
    cpf_limpo = re.sub(r"\D", "", reg_str)
    if cpf_limpo:
        for idx, u in enumerate(usuarios):
            u_cpf = re.sub(r"\D", "", str(u.get("cpf") or u.get("CPF") or ""))
            if u_cpf == cpf_limpo or (len(cpf_limpo) >= 6 and cpf_limpo in u_cpf):
                return idx, formatar_cliente_dict(u)

    # 3. Tentativa por Nome / Sobrenome
    termo_nome = reg_str.lower()
    for idx, u in enumerate(usuarios):
        nome_completo = f"{u.get('nome', '')} {u.get('sobrenome', '')}".lower()
        if termo_nome in nome_completo:
            return idx, formatar_cliente_dict(u)

    # Fallback: se não encontrou, avisa e usa o primeiro
    LOGGER.warning(
        f"Registro '{registro}' não encontrado no CSV. Utilizando o primeiro registro (índice 0) por padrão."
    )
    return 0, formatar_cliente_dict(usuarios[0])


def listar_registros_csv(limite: int = 20) -> List[Dict[str, Any]]:
    """Retorna a lista formatada de registros do CSV para exibição."""
    usuarios = carregar_usuarios()
    return [formatar_cliente_dict(u) for u in usuarios[:limite]]


def executar_processo_1(
    registro: Any = 0,
    modo: str = "unico",
    row_index: Optional[int] = None,
    email_destino: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Executa o Processo 1 de ponta a ponta:
    1. Carrega os dados do CSV (sem preenchimento prévio no portal fake).
    2. Seleciona o registro desejado a partir do parâmetro 'registro'.
    3. Gera o documento Word de Ficha de Cadastro (.docx).
    4. Dispara e-mail com a ficha em anexo para assinatura do cliente.
    """
    print("\n" + "=" * 70)
    print("🚀 [PROCESSO 1] INICIANDO GERAÇÃO E ENVIO DE FICHA A PARTIR DO CSV")
    print("=" * 70)

    email_destino_padrao = (
        email_destino
        or os.getenv("EMAIL_CLIENTE_TESTE")
        or os.getenv("EMAIL_REMETENTE")
        or "fani.souza19@gmail.com"
    )

    # Carrega base do CSV
    usuarios = carregar_usuarios()
    total_csv = len(usuarios)
    print(f"📊 Base do CSV carregada com sucesso ({total_csv} registros disponíveis).")

    # Mapeia row_index se fornecido explicitamente
    param_registro = row_index if (row_index is not None and registro == 0) else registro

    # Identifica se é modo todos ou único
    modo_todos = modo == "todos" or str(param_registro).strip().lower() == "todos"

    # Seleção dos dados para geração da ficha
    lista_clientes: List[Dict[str, Any]] = []
    if modo_todos:
        print("\n[Etapa 1] Modo 'TODOS' selecionado. Gerando fichas para todos os registros do CSV...")
        lista_clientes = [formatar_cliente_dict(u) for u in usuarios]
    else:
        idx_selecionado, cliente_sel = selecionar_cliente_csv(usuarios, param_registro)
        print(f"\n[Etapa 1] Registro selecionado do CSV para Ficha de Cadastro:")
        print(f"  • Linha/Índice: {idx_selecionado}")
        print(f"  • ID Solicitação: {cliente_sel.get('id_solicitacao')}")
        print(f"  • Nome Completo: {cliente_sel.get('Nome')} {cliente_sel.get('Sobrenome')}")
        print(f"  • CPF: {cliente_sel.get('CPF')}")
        print(f"  • E-mail: {cliente_sel.get('E-mail')}")
        print(f"  • Telefone: {cliente_sel.get('Telefone')}")
        lista_clientes = [cliente_sel]

    enviados: List[Dict[str, Any]] = []

    # Geração das Fichas (.docx) e Disparo dos E-mails
    print("\n[Etapa 2] Gerando Fichas de Cadastro (.docx) e Disparando E-mails...")
    for i, cliente in enumerate(lista_clientes, start=1):
        nome_completo = f"{cliente.get('Nome', '')} {cliente.get('Sobrenome', '')}".strip()
        print(f"\n  ({i}/{len(lista_clientes)}) Processando Ficha do Cliente: {nome_completo}")

        arquivo_docx = criar_documento(cliente)
        print(f"  📄 Ficha Word (.docx) gerada: {arquivo_docx}")

        destinatario = email_destino or cliente.get("E-mail") or email_destino_padrao
        print(f"  ✉️ Disparando e-mail para: {destinatario}")

        try:
            enviar_email(destinatario, arquivo_docx, apagar_apos_envio=True)
            enviados.append(
                {
                    "cliente": cliente,
                    "arquivo": arquivo_docx,
                    "email": destinatario,
                    "sucesso": True,
                }
            )
            print(f"  ✅ Ficha enviada com sucesso para {destinatario}!")
        except Exception as e:
            LOGGER.error(f"Falha ao enviar e-mail para {destinatario}: {e}")
            if os.path.exists(arquivo_docx):
                try:
                    os.remove(arquivo_docx)
                    print(f"  🗑️ Arquivo temporário '{Path(arquivo_docx).name}' removido após falha.")
                except Exception:
                    pass
            enviados.append(
                {
                    "cliente": cliente,
                    "arquivo": arquivo_docx,
                    "email": destinatario,
                    "sucesso": False,
                    "erro": str(e),
                }
            )

    print("\n" + "=" * 70)
    print(f"✅ [PROCESSO 1] CONCLUÍDO COM SUCESSO! ({len(enviados)} ficha(s) enviada(s))")
    print("⏳ Status: Aguardando o cliente assinar e retornar a documentação.")
    print("👉 Quando o cliente enviar os documentos (Ficha + Foto + Residência), execute o Processo 2.")
    print("=" * 70 + "\n")

    return enviados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 1 - Envio de Ficha de Cadastro para Assinatura a partir do CSV"
    )
    parser.add_argument(
        "--registro",
        default="0",
        help="Registro do CSV a ser utilizado: número da linha (0-19), ID da solicitação (1-20), CPF, nome ou 'todos'. Padrão: 0.",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=None,
        help="Índice numérico da linha no CSV (0 a N).",
    )
    parser.add_argument(
        "--cpf",
        default=None,
        help="CPF do cliente no CSV para gerar a ficha.",
    )
    parser.add_argument(
        "--id",
        "--id-solicitacao",
        dest="id_solicitacao",
        default=None,
        help="ID de solicitação do cliente no CSV.",
    )
    parser.add_argument(
        "--modo",
        choices=["unico", "todos"],
        default="unico",
        help="Modo de processamento: 'unico' (1 cliente) ou 'todos' (todos os clientes do CSV).",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="E-mail customizado de destino para receber a ficha gerada.",
    )

    args = parser.parse_args()

    param_registro = args.cpf or args.id_solicitacao or (args.row_index if args.row_index is not None else args.registro)

    executar_processo_1(
        registro=param_registro,
        modo=args.modo,
        row_index=args.row_index,
        email_destino=args.email,
    )


if __name__ == "__main__":
    main()
