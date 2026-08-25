"""
Processo 2 - Recebimento, Download e Validação Documental
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Ler e-mails (IMAP) com fichas assinadas e documentos anexos (ou ler pasta local).
2. Baixar os PDFs para a pasta de entrada.
3. Inspecionar e validar os 3 documentos obrigatórios:
   - Ficha Cadastral Assinada
   - Documento Oficial com Foto (RG / CNH / Identidade)
   - Comprovante de Residência
4. Se Aprovado: Move para Documentos_OK e Documentos_Aprovados/ e dispara e-mail de confirmação com protocolo.
5. Se Pendente: Move para Documentos_Pendentes e dispara e-mail notificando o que faltou.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import random
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"
DOCS_APROVADOS_DIR = RESOURCES_DIR / "Documentos_Aprovados"

sys.path.append(str(BASE_DIR))

from processo_atendimento.gestor_arquivos import GestorArquivos
from processo_atendimento.leitor_email import LeitorEmailIMAP
from processo_atendimento.resposta_cliente import RespostaClienteSMTP
from processo_atendimento.validador_docs import ValidadorDocs

LOGGER = logging.getLogger("PROCESSO_2_VALIDACAO")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(name)s] %(levelname)s: %(message)s")


def gerar_protocolo() -> str:
    """Gera protocolo único no formato #2026-XXXX."""
    sufixo = random.randint(1000, 9999)
    ano = datetime.datetime.now().year
    return f"#{ano}-{sufixo}"


def criar_exemplo_simulacao(gestor: GestorArquivos) -> List[Tuple[Path, str]]:
    """Gera PDFs de teste locais para modo simulação."""
    LOGGER.info("Gerando arquivos de teste locais na pasta Downloads/...")
    
    pdf_aprovado = gestor.pasta_downloads / "solicitacao_completa_ana_silva.pdf"
    texto_aprovado = (
        "Ficha Cadastral Assinada\n"
        "Nome: Ana Silva\n"
        "CPF: 111.222.333-44\n"
        "E-mail: ana.silva@exemplo.com\n"
        "Telefone: (92) 98888-1111\n"
        "Data de Nascimento: 15/05/1992\n"
        "Endereco: Rua das Palmeiras, 120 - Manaus/AM\n"
        "Documento Oficial com Foto: Carteira de Identidade RG 1234567-SSP\n"
        "Comprovante de Residência: Conta de Luz referente ao endereço Rua das Palmeiras, 120\n"
        "Assinatura do Cliente: Ana Silva\n"
    )
    pdf_aprovado.write_text(texto_aprovado, encoding="utf-8")

    pdf_pendente = gestor.pasta_downloads / "solicitacao_pendente_carlos_souza.pdf"
    texto_pendente = (
        "Ficha Cadastral Assinada\n"
        "Nome: Carlos Souza\n"
        "CPF: 999.888.777-66\n"
        "E-mail: carlos.souza@exemplo.com\n"
        "Assinatura do Cliente: Carlos Souza\n"
    )
    pdf_pendente.write_text(texto_pendente, encoding="utf-8")

    return [
        (pdf_aprovado, "ana.silva@exemplo.com"),
        (pdf_pendente, "carlos.souza@exemplo.com"),
    ]


def executar_processo_2(
    modo: str = "real",
    notificar_cliente: bool = True,
    termos_busca: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Executa o Processo 2: Baixa os e-mails, valida documentos e classifica.
    Retorna dicionário com listas de PDFs aprovados e pendentes.
    """
    print("\n" + "=" * 70)
    print(f"📥 [PROCESSO 2] INICIANDO VALIDAÇÃO DE DOCUMENTAÇÃO (Modo: {modo.upper()})")
    print("=" * 70)

    gestor = GestorArquivos()
    gestor.garantir_estrutura_diretorios()
    DOCS_APROVADOS_DIR.mkdir(parents=True, exist_ok=True)

    leitor = LeitorEmailIMAP(gestor)
    validador = ValidadorDocs()
    resposta = RespostaClienteSMTP()

    if modo == "real":
        print("\n[Etapa 1] Conectando ao servidor IMAP para buscar novos e-mails...")
        itens_processar = leitor.ler_emails_pendentes(termos_busca=termos_busca)
    else:
        print("\n[Etapa 1] Gerando dados de simulação locais...")
        itens_processar = criar_exemplo_simulacao(gestor)

    if not itens_processar:
        print("\n⚠️ Nenhum novo arquivo PDF encontrado para validação.")
        return {"aprovados": [], "pendentes": [], "dados_clientes": []}

    print(f"\n[Etapa 2] {len(itens_processar)} arquivo(s) localizado(s). Iniciando inspeção documental...")

    aprovados: List[Path] = []
    pendentes: List[Path] = []
    dados_clientes: List[Dict[str, Any]] = []

    for i, (item_arquivos, email_remetente) in enumerate(itens_processar, start=1):
        lista_arqs = item_arquivos if isinstance(item_arquivos, list) else [item_arquivos]
        lista_arqs = [a for a in lista_arqs if a.exists()]
        if not lista_arqs:
            continue

        protocolo = gerar_protocolo()
        nomes_arqs = ", ".join(a.name for a in lista_arqs)
        print(f"\n------------------------------------------------------------")
        print(f"📄 ({i}/{len(itens_processar)}) Analisando solicitação ({len(lista_arqs)} arquivo(s)): {nomes_arqs}")
        print(f"   Protocolo: {protocolo} | Remetente: {email_remetente}")

        is_aprovado, lista_pendencias, dados_cliente = validador.validar_documentos_arquivos(lista_arqs)
        dados_cliente["protocolo"] = protocolo
        if email_remetente and email_remetente != "cliente@example.com":
            dados_cliente["email"] = email_remetente

        destinatario = dados_cliente.get("email") or email_remetente

        if is_aprovado:
            print(f"  ✅ STATUS: APROVADO (Todos os documentos obrigatórios presentes)")

            # Move os arquivos para Documentos_OK e copia PDFs para Documentos_Aprovados
            for arq in lista_arqs:
                arq_ok = gestor.mover_para_documentos_ok(arq)
                if arq_ok.suffix.lower() == ".pdf":
                    destino_aprovados = DOCS_APROVADOS_DIR / arq_ok.name
                    shutil.copy2(str(arq_ok), str(destino_aprovados))
                    aprovados.append(destino_aprovados)

            dados_clientes.append(dados_cliente)

            if notificar_cliente:
                print(f"  ✉️ Enviando confirmação de aprovação para: {destinatario}")
                try:
                    resposta.enviar_resposta_cliente(
                        email_destino=destinatario,
                        aprovado=True,
                        protocolo=protocolo,
                        dados_cliente=dados_cliente,
                    )
                except Exception as e:
                    LOGGER.warning(f"Não foi possível enviar e-mail: {e}")

        else:
            print(f"  ⚠️ STATUS: PENDENTE (Faltam: {', '.join(lista_pendencias)})")

            # Move para Documentos_Pendentes
            for arq in lista_arqs:
                arq_pend = gestor.mover_para_documentos_pendentes(arq)
                pendentes.append(arq_pend)

            if notificar_cliente:
                print(f"  ✉️ Enviando notificação de pendência para: {destinatario}")
                try:
                    resposta.enviar_resposta_cliente(
                        email_destino=destinatario,
                        aprovado=False,
                        protocolo=protocolo,
                        pendencias=lista_pendencias,
                        dados_cliente=dados_cliente,
                    )
                except Exception as e:
                    LOGGER.warning(f"Não foi possível enviar e-mail: {e}")

    print("\n" + "=" * 70)
    print("📊 [PROCESSO 2] RESUMO DA VALIDAÇÃO:")
    print(f"  • Total de Solicitações Analisadas: {len(itens_processar)}")
    print(f"  • Solicitações Aprovadas: {len(dados_clientes)}")
    print(f"  • Arquivos com Pendências: {len(pendentes)}")
    print("=" * 70 + "\n")

    # Se houver aprovados, extrai automaticamente para a Planilha Mestra (Processo 2 - Organização)
    if aprovados:
        try:
            from processo_3_extracao_planilha import executar_processo_3 as extrair_para_planilha_mestra
            print("🔗 [PROCESSO 2] Extraindo dados dos documentos aprovados para a Planilha Mestra...")
            extrair_para_planilha_mestra(lista_pdfs=aprovados)
        except Exception as erro_extracao:
            LOGGER.error(f"Erro ao extrair dados para planilha mestra: {erro_extracao}")

    return {
        "aprovados": aprovados,
        "pendentes": pendentes,
        "dados_clientes": dados_clientes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 2 - Recebimento, Download e Validação Documental"
    )
    parser.add_argument(
        "--modo",
        choices=["real", "simulacao"],
        default="real",
        help="Modo de execução: 'real' (consulta e-mail IMAP) ou 'simulacao' (arquivos locais).",
    )
    parser.add_argument(
        "--no-reply",
        action="store_true",
        help="Desativa o disparo automático de e-mail de resposta para o cliente.",
    )

    args = parser.parse_args()
    executar_processo_2(
        modo=args.modo,
        notificar_cliente=not args.no_reply,
    )


if __name__ == "__main__":
    main()
