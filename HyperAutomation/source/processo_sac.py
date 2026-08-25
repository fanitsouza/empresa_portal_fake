"""
Processo 4 - Setor de SAC (Serviço de Atendimento ao Cliente)
Portal Fake Soluções Digitais - Hyperautomation

Responsabilidade:
1. Receber o status dos cadastros (da Planilha Mestra ou do Processo 3).
2. Consultar a Planilha Mestra e analisar o resultado de cada cliente:
   - Se o cadastro foi realizado com SUCESSO:
     * Envia e-mail de confirmação e boas-vindas com protocolo.
     * Atualiza a planilha Status_SAC com 'CONFIRMACAO_ENVIADA'.
   - Se o cadastro NÃO foi realizado com sucesso (Duplicado ou Erro):
     * Envia e-mail informando o motivo detalhado do erro com protocolo.
     * Atualiza a planilha Status_SAC com 'NOTIFICACAO_ERRO_ENVIADA'.
3. Gerar e salvar a planilha consolidada 'resources/Status_SAC.xlsx'.
4. Atualizar o status do SAC na Planilha Mestra (.xlsx).
5. Encaminhar os dados estruturados para o Processo 5 (Relatórios) gerando 'resources/relatorio_sac.json'.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import logging
import os
from pathlib import Path
import random
import re
import shutil
import smtplib
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parent
PATH_ROOT = BASE_DIR.parent
RESOURCES_DIR = PATH_ROOT / "resources"

PLANILHA_MESTRA_PADRAO = RESOURCES_DIR / "planilha_mestra.xlsx"
PLANILHA_SAC_PADRAO = RESOURCES_DIR / "Status_SAC.xlsx"
RELATORIO_JSON_PADRAO = RESOURCES_DIR / "relatorio_sac.json"
PASTA_ERP = RESOURCES_DIR / "ERP_Portal_Fake"
PASTA_LOGS = RESOURCES_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from planilha_mestra import atualizar_status_sac_planilha, carregar_registros_planilha

LOGGER = logging.getLogger("PROCESSO_4_SAC")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(name)s] %(levelname)s: %(message)s")


COLUNAS_STATUS_SAC = [
    "Protocolo SAC",
    "Data Registro",
    "Nome Cliente",
    "CPF",
    "E-mail",
    "Telefone",
    "Status Cadastro",
    "Status SAC",
    "Motivo Erro / Observação",
    "E-mail Enviado",
    "Atualizado em",
]


def gerar_protocolo_sac() -> str:
    """Gera um protocolo exclusivo do SAC no formato #SAC-2026-XXXX."""
    sufixo = random.randint(1000, 9999)
    ano = datetime.now().year
    return f"#SAC-{ano}-{sufixo}"


def mascarar_cpf(cpf: str) -> str:
    """Formata o CPF para exibição segura com máscara."""
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) == 11:
        return f"***.{digitos[3:6]}.***-{digitos[9:]}"
    return cpf or "Não informado"


class GeradorEmailSAC:
    """Gera templates HTML corporativos e gerencia o envio SMTP para o SAC."""

    def __init__(self) -> None:
        self.host = (os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER") or "smtp.gmail.com").strip()
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.email_remetente = (os.getenv("EMAIL_REMETENTE") or os.getenv("SMTP_USER") or "").strip()
        self.senha_app = (os.getenv("EMAIL_SENHA_APP") or os.getenv("EMAIL_SENHA") or os.getenv("SMTP_PASSWORD") or "").strip()

    def gerar_html_confirmacao_sucesso(
        self,
        nome_cliente: str,
        protocolo: str,
        cliente: Dict[str, Any],
    ) -> str:
        """Template HTML corporativo para confirmação de cadastro concluído com sucesso."""
        cpf_mascarado = mascarar_cpf(cliente.get("cpf", ""))
        email_cliente = cliente.get("email", "Não informado")
        telefone = cliente.get("telefone", "Não informado")
        endereco = cliente.get("endereco", "Não informado")

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #0f172a, #1e3a8a, #2563eb); color: #ffffff; padding: 30px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .header p {{ margin: 6px 0 0 0; opacity: 0.9; font-size: 14px; }}
    .content {{ padding: 32px 28px; color: #334155; line-height: 1.6; }}
    .badge {{ display: inline-block; background: #dcfce7; color: #166534; font-weight: 700; font-size: 13px; padding: 6px 14px; border-radius: 20px; margin-bottom: 18px; border: 1px solid #bbf7d0; }}
    .protocolo-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #2563eb; padding: 14px 18px; border-radius: 6px; margin: 20px 0; }}
    .protocolo-box .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
    .protocolo-box .valor {{ font-size: 18px; font-family: 'Courier New', Courier, monospace; color: #1e293b; font-weight: 700; }}
    .resumo-tabela {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
    .resumo-tabela td {{ padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
    .resumo-tabela td.label {{ width: 35%; color: #64748b; font-weight: 600; background: #f1f5f9; }}
    .resumo-tabela td.val {{ color: #1e293b; }}
    .passos {{ background: #eff6ff; border-radius: 8px; padding: 18px; margin: 20px 0; border: 1px solid #dbeafe; }}
    .passos h4 {{ margin: 0 0 10px 0; color: #1e40af; font-size: 15px; }}
    .passos ul {{ margin: 0; padding-left: 20px; }}
    .passos li {{ margin-bottom: 6px; font-size: 13.5px; color: #1e3a8a; }}
    .footer {{ background: #f8fafc; text-align: center; padding: 18px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>PORTAL FAKE SOLUÇÕES DIGITAIS</h1>
      <p>Serviço de Atendimento ao Cliente (SAC) - Confirmação de Cadastro</p>
    </div>
    <div class="content">
      <div class="badge">✓ CADASTRO CONCLUÍDO COM SUCESSO</div>
      <h2 style="margin: 0 0 12px 0; color: #0f172a; font-size: 20px;">Olá, {nome_cliente}!</h2>
      <p>É com grande satisfação que confirmamos que o seu cadastro foi <strong>processado, validado e ativado com sucesso</strong> em nossa plataforma corporativa.</p>
      
      <div class="protocolo-box">
        <div class="label">Protocolo de Atendimento SAC</div>
        <div class="valor">{protocolo}</div>
      </div>

      <h3 style="color: #0f172a; font-size: 16px; margin: 20px 0 8px 0;">📋 Resumo dos Dados Cadastrados:</h3>
      <table class="resumo-tabela">
        <tr>
          <td class="label">Nome Completo</td>
          <td class="val">{nome_cliente}</td>
        </tr>
        <tr>
          <td class="label">CPF</td>
          <td class="val"><code>{cpf_mascarado}</code></td>
        </tr>
        <tr>
          <td class="label">E-mail</td>
          <td class="val">{email_cliente}</td>
        </tr>
        <tr>
          <td class="label">Telefone</td>
          <td class="val">{telefone}</td>
        </tr>
        <tr>
          <td class="label">Endereço</td>
          <td class="val">{endereco}</td>
        </tr>
        <tr>
          <td class="label">Status do Cadastro</td>
          <td class="val"><strong style="color: #16a34a;">ATIVO NO SISTEMA</strong></td>
        </tr>
      </table>

      <div class="passos">
        <h4>🚀 Próximas Etapas e Acesso:</h4>
        <ul>
          <li>Seu perfil já está habilitado para utilização dos serviços digitais.</li>
          <li>Em caso de dúvidas ou necessidade de alteração cadastral, informe sempre o seu protocolo SAC.</li>
        </ul>
      </div>

      <p style="font-size: 14px; margin-top: 24px;">Seja muito bem-vindo(a)!<br>
      <strong>Equipe de Atendimento ao Cliente - SAC</strong><br>
      Portal Fake Soluções Digitais</p>
    </div>
    <div class="footer">
      Portal Fake Soluções Digitais S.A. &copy; 2026 - Todos os direitos reservados.<br>
      Este é um e-mail automático gerado pelo sistema de Hyperautomation.
    </div>
  </div>
</body>
</html>"""

    def gerar_html_notificacao_erro(
        self,
        nome_cliente: str,
        protocolo: str,
        motivo_erro: str,
        cliente: Dict[str, Any],
    ) -> str:
        """Template HTML corporativo para notificação de erro ou duplicidade no cadastro."""
        cpf_mascarado = mascarar_cpf(cliente.get("cpf", ""))

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #7f1d1d, #991b1b, #dc2626); color: #ffffff; padding: 30px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .header p {{ margin: 6px 0 0 0; opacity: 0.9; font-size: 14px; }}
    .content {{ padding: 32px 28px; color: #334155; line-height: 1.6; }}
    .badge {{ display: inline-block; background: #fee2e2; color: #991b1b; font-weight: 700; font-size: 13px; padding: 6px 14px; border-radius: 20px; margin-bottom: 18px; border: 1px solid #fecaca; }}
    .alert-box {{ background: #fff5f5; border: 1px solid #fecaca; border-left: 5px solid #ef4444; padding: 16px 20px; border-radius: 6px; margin: 20px 0; }}
    .alert-box h4 {{ margin: 0 0 8px 0; color: #991b1b; font-size: 15px; }}
    .alert-box p {{ margin: 0; color: #7f1d1d; font-size: 14px; }}
    .protocolo-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #64748b; padding: 14px 18px; border-radius: 6px; margin: 20px 0; }}
    .protocolo-box .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
    .protocolo-box .valor {{ font-size: 18px; font-family: 'Courier New', Courier, monospace; color: #1e293b; font-weight: 700; }}
    .instrucoes {{ background: #f8fafc; border-radius: 8px; padding: 18px; margin: 20px 0; border: 1px solid #e2e8f0; }}
    .instrucoes h4 {{ margin: 0 0 10px 0; color: #334155; font-size: 15px; }}
    .instrucoes ol {{ margin: 0; padding-left: 20px; }}
    .instrucoes li {{ margin-bottom: 6px; font-size: 13.5px; color: #475569; }}
    .footer {{ background: #f8fafc; text-align: center; padding: 18px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>PORTAL FAKE SOLUÇÕES DIGITAIS</h1>
      <p>Serviço de Atendimento ao Cliente (SAC) - Comunicado Cadastral</p>
    </div>
    <div class="content">
      <div class="badge">⚠️ INCONSISTÊNCIA IDENTIFICADA NO CADASTRO</div>
      <h2 style="margin: 0 0 12px 0; color: #0f172a; font-size: 20px;">Olá, {nome_cliente}!</h2>
      <p>Durante a rotina automatizada de inclusão do seu cadastro em nosso sistema corporativo, identificamos uma inconsistência que impediu a conclusão do registro.</p>
      
      <div class="alert-box">
        <h4>Motivo do Erro / Inconsistência:</h4>
        <p><strong>{motivo_erro}</strong></p>
        <p style="margin-top: 8px; font-size: 13px; color: #991b1b;">CPF sob análise: <code>{cpf_mascarado}</code></p>
      </div>

      <div class="protocolo-box">
        <div class="label">Protocolo SAC para Acompanhamento</div>
        <div class="valor">{protocolo}</div>
      </div>

      <div class="instrucoes">
        <h4>📌 Como Proceder para Regularização:</h4>
        <ol>
          <li>Se você já possui cadastro ativo em nossa base, acesse diretamente o portal utilizando suas credenciais cadastradas anteriormente.</li>
          <li>Caso não reconheça o cadastro existente ou precise atualizar informações, responda a este e-mail anexando seu documento com foto.</li>
          <li>Nossa equipe de atendimento prestará o suporte necessário com base no protocolo informado.</li>
        </ol>
      </div>

      <p style="font-size: 14px; margin-top: 24px;">Estamos à inteira disposição para auxiliá-lo(a).<br>
      <strong>Equipe de Atendimento ao Cliente - SAC</strong><br>
      Portal Fake Soluções Digitais</p>
    </div>
    <div class="footer">
      Portal Fake Soluções Digitais S.A. &copy; 2026 - Todos os direitos reservados.<br>
      Este é um e-mail automático gerado pelo sistema de Hyperautomation.
    </div>
  </div>
</body>
</html>"""

    def enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo_html: str,
    ) -> Tuple[bool, str]:
        """Dispara o e-mail via SMTP SSL ou simula se as credenciais não estiverem presentes."""
        if not self.email_remetente or not self.senha_app:
            LOGGER.warning(
                f"[SAC E-MAIL] Credenciais SMTP não configuradas. Modo simulação ativo para: {destinatario}"
            )
            return True, "Simulado (Sem credenciais)"

        mensagem = MIMEMultipart("alternative")
        mensagem["Subject"] = assunto
        mensagem["From"] = self.email_remetente
        mensagem["To"] = destinatario
        mensagem.attach(MIMEText(corpo_html, "html", "utf-8"))

        try:
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=15.0) as server:
                    server.login(self.email_remetente, self.senha_app)
                    server.sendmail(self.email_remetente, destinatario, mensagem.as_string())
            else:
                with smtplib.SMTP(self.host, self.port, timeout=15.0) as server:
                    server.starttls()
                    server.login(self.email_remetente, self.senha_app)
                    server.sendmail(self.email_remetente, destinatario, mensagem.as_string())
            LOGGER.info(f"[SAC E-MAIL] E-mail enviado com sucesso para: {destinatario}")
            return True, "Enviado com sucesso"
        except Exception as e:
            LOGGER.error(f"[SAC E-MAIL] Falha ao enviar e-mail para {destinatario}: {e}")
            return False, str(e)


def salvar_planilha_status_sac(
    registros_sac: List[Dict[str, Any]],
    caminho_planilha: Path | str = PLANILHA_SAC_PADRAO,
) -> Path:
    """Cria ou atualiza a planilha Status_SAC.xlsx com layout e formatação profissional."""
    caminho = Path(caminho_planilha).resolve()
    caminho.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    planilha = workbook.active
    planilha.title = "Status SAC"

    # Cabeçalho
    planilha.append(COLUNAS_STATUS_SAC)

    # Estilos
    cor_cabecalho = PatternFill("solid", fgColor="1E3A8A")
    fonte_cabecalho = Font(color="FFFFFF", bold=True, size=11, name="Segoe UI")
    alinhamento_cabecalho = Alignment(horizontal="center", vertical="center", wrap_text=True)

    borda_fina = Side(style="thin", color="CBD5E1")
    borda_celula = Border(left=borda_fina, right=borda_fina, top=borda_fina, bottom=borda_fina)

    for celula in planilha[1]:
        celula.fill = cor_cabecalho
        celula.font = fonte_cabecalho
        celula.alignment = alinhamento_cabecalho

    # Preenchimento de dados
    cor_sucesso = PatternFill("solid", fgColor="DCFCE7")
    cor_duplicado = PatternFill("solid", fgColor="FEF3C7")
    cor_erro = PatternFill("solid", fgColor="FEE2E2")

    fonte_sucesso = Font(color="166534", bold=True, size=10, name="Segoe UI")
    fonte_duplicado = Font(color="92400E", bold=True, size=10, name="Segoe UI")
    fonte_erro = Font(color="991B1B", bold=True, size=10, name="Segoe UI")

    for reg in registros_sac:
        linha_valores = [
            reg.get("protocolo", ""),
            reg.get("data_registro", ""),
            reg.get("nome_cliente", ""),
            reg.get("cpf", ""),
            reg.get("email", ""),
            reg.get("telefone", ""),
            reg.get("status_cadastro", ""),
            reg.get("status_sac", ""),
            reg.get("motivo_erro", ""),
            reg.get("email_enviado", ""),
            reg.get("atualizado_em", ""),
        ]
        planilha.append(linha_valores)
        num_linha = planilha.max_row

        # Formatação das linhas
        status_cad = str(reg.get("status_cadastro", "")).upper()
        for col_idx in range(1, len(COLUNAS_STATUS_SAC) + 1):
            cel = planilha.cell(row=num_linha, column=col_idx)
            cel.border = borda_celula
            cel.font = Font(size=10, name="Segoe UI")

            # Destaca a coluna de Status SAC
            if col_idx == 8:  # Status SAC
                if "CONFIRMACAO" in status_cad or "SUCESSO" in status_cad:
                    cel.fill = cor_sucesso
                    cel.font = fonte_sucesso
                elif "DUPLICADO" in status_cad:
                    cel.fill = cor_duplicado
                    cel.font = fonte_duplicado
                else:
                    cel.fill = cor_erro
                    cel.font = fonte_erro

    # Ajusta larguras das colunas
    larguras = {
        "A": 20,  # Protocolo SAC
        "B": 20,  # Data Registro
        "C": 28,  # Nome Cliente
        "D": 18,  # CPF
        "E": 30,  # E-mail
        "F": 18,  # Telefone
        "G": 20,  # Status Cadastro
        "H": 28,  # Status SAC
        "I": 45,  # Motivo Erro
        "J": 24,  # E-mail Enviado
        "K": 22,  # Atualizado em
    }
    for col_letter, width in larguras.items():
        planilha.column_dimensions[col_letter].width = width

    planilha.auto_filter.ref = planilha.dimensions
    planilha.freeze_panes = "A2"
    workbook.save(caminho)

    # Cria cópia no ERP_Portal_Fake para facilidade de auditoria
    copia_erp = PASTA_ERP / "Status_SAC.xlsx"
    try:
        shutil.copy2(str(caminho), str(copia_erp))
    except Exception:
        pass

    return caminho


def exportar_relatorio_processo_5(
    registros_sac: List[Dict[str, Any]],
    caminho_saida: Path | str = RELATORIO_JSON_PADRAO,
) -> Path:
    """Consolida as métricas do SAC em JSON para alimentação direta do Processo 5 (Relatórios)."""
    caminho = Path(caminho_saida).resolve()
    caminho.parent.mkdir(parents=True, exist_ok=True)

    total = len(registros_sac)
    sucessos = sum(1 for r in registros_sac if "SUCESSO" in str(r.get("status_cadastro", "")).upper())
    duplicados = sum(1 for r in registros_sac if "DUPLICADO" in str(r.get("status_cadastro", "")).upper())
    erros = total - (sucessos + duplicados)

    relatorio = {
        "processo": "Processo 4 - SAC (Serviço de Atendimento ao Cliente)",
        "proximo_processo": "Processo 5 - Relatórios e Métricas de Performance",
        "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "resumo_metricas": {
            "total_solicitacoes_sac": total,
            "cadastros_confirmados_com_sucesso": sucessos,
            "cadastros_duplicados_notificados": duplicados,
            "cadastros_erros_notificados": erros,
            "taxa_sucesso_cadastros_pct": round((sucessos / total * 100) if total > 0 else 0, 2),
        },
        "atendimentos_sac": registros_sac,
    }

    caminho.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


def executar_processo_sac(
    caminho_planilha: Path | str | None = None,
    resultados_processo_3: Optional[List[Dict[str, Any]]] = None,
    email_teste: Optional[str] = None,
    enviar_email: bool = True,
) -> Dict[str, Any]:
    """
    Executa o Processo 4 (SAC):
    1. Recebe status do cadastro da Planilha Mestra ou do Processo 3
    2. Envia e-mails corporativos diferenciados (Sucesso vs Erro/Duplicado)
    3. Cria e preenche a planilha Status_SAC.xlsx
    4. Atualiza a Planilha Mestra
    5. Exporta relatório consolidado para o Processo 5
    """
    print("\n" + "=" * 70)
    print("🎧 [PROCESSO 4] INICIANDO SAC - SERVIÇO DE ATENDIMENTO AO CLIENTE")
    print("=" * 70)

    planilha_mestra = Path(caminho_planilha) if caminho_planilha else PLANILHA_MESTRA_PADRAO
    gerador_email = GeradorEmailSAC()

    # 1. Obtenção dos Registros
    registros_analisar: List[Dict[str, Any]] = []

    if resultados_processo_3:
        print(f"\n[Etapa 1] Recebidos {len(resultados_processo_3)} registros diretamente do Processo 3.")
        for item in resultados_processo_3:
            cli = item.get("cliente") or {}
            registros_analisar.append({
                "nome": cli.get("nome_completo") or cli.get("Nome") or item.get("nome", "Cliente"),
                "cpf": item.get("cpf") or cli.get("cpf") or cli.get("CPF", ""),
                "email": cli.get("email") or cli.get("E-mail", ""),
                "telefone": cli.get("telefone") or cli.get("Telefone", ""),
                "endereco": cli.get("endereco") or cli.get("Endereco", ""),
                "status_cadastro": item.get("status_cadastro", "SUCESSO"),
                "motivo_erro": item.get("motivo_erro", ""),
            })
    else:
        print(f"\n[Etapa 1] Consultando status de cadastro na Planilha Mestra: {planilha_mestra.name}")
        try:
            linhas_planilha = carregar_registros_planilha(planilha_mestra)
            for linha in linhas_planilha:
                nome = linha.get("Nome", "").strip()
                cpf = linha.get("CPF", "").strip()
                if not nome or not cpf:
                    continue
                
                status_cad = linha.get("Status Cadastro", "").strip() or "SUCESSO"
                motivo = linha.get("Motivo Erro Cadastro", "").strip()

                registros_analisar.append({
                    "nome": nome,
                    "cpf": cpf,
                    "email": linha.get("E-mail", "").strip(),
                    "telefone": linha.get("Telefone", "").strip(),
                    "endereco": linha.get("Endereco", "").strip(),
                    "status_cadastro": status_cad,
                    "motivo_erro": motivo,
                })
        except Exception as e:
            LOGGER.error(f"Falha ao ler a planilha mestra: {e}")
            return {"total": 0, "sucessos": 0, "erros": 0, "registros": []}

    if not registros_analisar:
        print("ℹ️ Nenhum registro encontrado para processamento no SAC.")
        return {"total": 0, "sucessos": 0, "erros": 0, "registros": []}

    total = len(registros_analisar)
    print(f"  • {total} solicitação(ões) identificada(s) para atendimento SAC.")

    # 2. Processamento e Disparo de E-mails
    print(f"\n[Etapa 2] Processando atendimentos e gerando notificações personalizadas...")
    registros_sac: List[Dict[str, Any]] = []
    sucessos = 0
    notificacoes_erro = 0

    data_agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    for i, reg in enumerate(registros_analisar, start=1):
        protocolo = gerar_protocolo_sac()
        nome = reg.get("nome", "Prezado(a) Cliente")
        cpf = reg.get("cpf", "")
        email_dest = email_teste or reg.get("email") or os.getenv("EMAIL_REMETENTE") or "cliente@exemplo.com"
        status_cad = str(reg.get("status_cadastro", "SUCESSO")).upper()
        motivo_erro = reg.get("motivo_erro", "")

        print(f"\n------------------------------------------------------------")
        print(f"🎧 ({i}/{total}) Atendimento: {nome} | Protocolo: {protocolo}")
        print(f"  • Status Cadastro: {status_cad}")

        is_sucesso = ("SUCESSO" in status_cad or "ATIVO" in status_cad or "CONCLUIDO" in status_cad) and ("ERRO" not in status_cad and "DUPLICADO" not in status_cad)

        if is_sucesso:
            print(f"  ✉️ Tipo de Ação: ENVIO DE CONFIRMAÇÃO DE CADASTRO ATIVO")
            assunto = f"[Portal Fake SAC] Confirmação de Cadastro Aprovado - Protocolo {protocolo}"
            corpo_html = gerador_email.gerar_html_confirmacao_sucesso(nome, protocolo, reg)
            status_sac = "CONFIRMACAO_ENVIADA"
            sucessos += 1
        else:
            motivo_desc = motivo_erro or ("Cadastro Duplicado: CPF já existente na base" if "DUPLICADO" in status_cad else "Inconsistência cadastral nos dados fornecidos")
            print(f"  ✉️ Tipo de Ação: NOTIFICAÇÃO DE INCONSISTÊNCIA ({motivo_desc})")
            assunto = f"[Portal Fake SAC] Notificação sobre o seu Cadastro - Protocolo {protocolo}"
            corpo_html = gerador_email.gerar_html_notificacao_erro(nome, protocolo, motivo_desc, reg)
            status_sac = "NOTIFICACAO_ERRO_ENVIADA"
            notificacoes_erro += 1

        # Envio do e-mail
        if enviar_email:
            print(f"  🚀 Disparando e-mail para: {email_dest}...")
            ok_envio, desc_envio = gerador_email.enviar_email(email_dest, assunto, corpo_html)
            print(f"  {'✅' if ok_envio else '⚠️'} Resultado do envio: {desc_envio}")
        else:
            desc_envio = "Não enviado (Opção desativada)"
            print(f"  ℹ️ Envio de e-mail suprimido (--no-email). Gravando apenas na planilha.")

        registros_sac.append({
            "protocolo": protocolo,
            "data_registro": data_agora_str,
            "nome_cliente": nome,
            "cpf": cpf,
            "email": email_dest,
            "telefone": reg.get("telefone", ""),
            "status_cadastro": status_cad,
            "status_sac": status_sac,
            "motivo_erro": motivo_erro if not is_sucesso else "Cadastro realizado com sucesso",
            "email_enviado": desc_envio,
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    # 3. Geração da Planilha Status_SAC.xlsx
    print(f"\n[Etapa 3] Gerando e formatando a planilha corporativa: Status_SAC.xlsx...")
    caminho_planilha_sac = salvar_planilha_status_sac(registros_sac, PLANILHA_SAC_PADRAO)
    print(f"  📗 Planilha Status_SAC salva com sucesso em: {caminho_planilha_sac.name}")

    # 4. Atualização da Planilha Mestra
    print(f"\n[Etapa 4] Atualizando colunas de SAC na Planilha Mestra...")
    try:
        atualizar_status_sac_planilha(registros_sac, planilha_mestra)
        print(f"  📗 Planilha Mestra atualizada com status SAC: {planilha_mestra.name}")
    except Exception as e:
        LOGGER.warning(f"Não foi possível atualizar SAC na planilha mestra: {e}")

    # 5. Encaminhamento para o Processo 5 (Relatórios)
    print(f"\n[Etapa 5] Consolidando e exportando dados para o Processo 5 (Relatórios)..." )
    caminho_relatorio = exportar_relatorio_processo_5(registros_sac, RELATORIO_JSON_PADRAO)
    print(f"  📊 Pacote de dados para Relatórios gerado: {caminho_relatorio.name}")

    print("\n" + "=" * 70)
    print("📊 [PROCESSO 4 - SAC] RESUMO DO ATENDIMENTO:")
    print(f"  • Total de Solicitações Atendidas: {total}")
    print(f"  • Confirmações de Sucesso Enviadas: {sucessos}")
    print(f"  • Notificações de Erro/Duplicidade: {notificacoes_erro}")
    print(f"  • Planilha Status SAC: {caminho_planilha_sac}")
    print(f"  • Relatório Integrado (Processo 5): {caminho_relatorio}")
    print("=" * 70 + "\n")

    return {
        "total": total,
        "sucessos": sucessos,
        "erros": notificacoes_erro,
        "planilha_sac": caminho_planilha_sac,
        "relatorio_json": caminho_relatorio,
        "registros": registros_sac,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processo 4 - SAC (Serviço de Atendimento ao Cliente) - Notificações e Planilha Status_SAC"
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        default=str(PLANILHA_MESTRA_PADRAO),
        help="Caminho da Planilha Mestra .xlsx (padrão: resources/planilha_mestra.xlsx).",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="E-mail de destino customizado para teste dos disparos do SAC.",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Desativa o disparo SMTP de e-mails, gerando apenas a planilha Status_SAC.",
    )

    args = parser.parse_args()

    executar_processo_sac(
        caminho_planilha=args.planilha,
        email_teste=args.email,
        enviar_email=not args.no_email,
    )


if __name__ == "__main__":
    main()
