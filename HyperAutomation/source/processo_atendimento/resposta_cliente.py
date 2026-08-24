from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Dict, List, Optional

from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("RESPOSTA_CLIENTE")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

def carregar_env() -> None:
    path_atual = Path(__file__).resolve()
    candidatos = [
        path_atual.parents[1] / ".env",
        path_atual.parents[2] / ".env",
        path_atual.parents[3] / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "HyperAutomation" / "source" / ".env",
    ]
    for env_path in candidatos:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break
    else:
        load_dotenv()

carregar_env()


class RespostaClienteSMTP:
    """Dispara e-mails transacionais em HTML corporativo responsivo via SMTP."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        self.port = int(os.getenv("SMTP_PORT", "465"))
        self.email_remetente = (os.getenv("EMAIL_REMETENTE") or "").strip()
        self.senha_app = (os.getenv("EMAIL_SENHA_APP") or os.getenv("EMAIL_SENHA") or "").strip()


    def _gerar_html_sucesso(self, nome_cliente: str, protocolo: str) -> str:
        """Retorna o HTML responsivo para aprovação do cadastro."""
        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: #ffffff; padding: 24px; text-align: center; }}
            .content {{ padding: 30px; color: #334155; line-height: 1.6; }}
            .badge {{ display: inline-block; background: #dcfce7; color: #15803d; font-weight: bold; padding: 6px 12px; border-radius: 20px; margin-bottom: 15px; }}
            .protocolo {{ background: #f1f5f9; padding: 12px; border-left: 4px solid #3b82f6; font-family: monospace; font-size: 16px; margin: 15px 0; }}
            .footer {{ background: #f8fafc; text-align: center; padding: 16px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <h2 style="margin:0;">Portal Fake Soluções Digitais</h2>
              <p style="margin:5px 0 0 0; opacity:0.9;">Setor de Atendimento ao Cliente</p>
            </div>
            <div class="content">
              <div class="badge">✓ CADASTRO APROVADO E ATIVADO</div>
              <h3>Olá, {nome_cliente}!</h3>
              <p>Temos o prazer de informar que a sua documentação foi <strong>validada com sucesso</strong> e o seu cadastro já se encontra <strong>ATIVO</strong> em nosso sistema ERP.</p>
              
              <div class="protocolo">
                <strong>Protocolo de Atendimento:</strong> {protocolo}
              </div>

              <p><strong>Próximos Passos:</strong></p>
              <ul>
                <li>Sua solicitação foi encaminhada para o setor de integração operacional.</li>
                <li>Você receberá em breve o acesso aos nossos serviços digitais.</li>
              </ul>
              <p>Agradecemos a parceria!</p>
            </div>
            <div class="footer">
              Portal Fake Soluções Digitais &copy; 2026 - Todos os direitos reservados.
            </div>
          </div>
        </body>
        </html>
        """

    def _gerar_html_pendencia(
        self, nome_cliente: str, protocolo: str, pendencias: List[str]
    ) -> str:
        """Retorna o HTML responsivo destacado para pendências documentais."""
        itens_html = "".join(f"<li style='margin-bottom:8px;'><strong>{item}</strong></li>" for item in pendencias)

        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #991b1b, #ef4444); color: #ffffff; padding: 24px; text-align: center; }}
            .content {{ padding: 30px; color: #334155; line-height: 1.6; }}
            .badge {{ display: inline-block; background: #fee2e2; color: #b91c1c; font-weight: bold; padding: 6px 12px; border-radius: 20px; margin-bottom: 15px; }}
            .alert-box {{ background: #fff5f5; border: 1px solid #fecaca; border-left: 4px solid #ef4444; padding: 15px; border-radius: 4px; margin: 15px 0; }}
            .protocolo {{ background: #f1f5f9; padding: 12px; border-left: 4px solid #94a3b8; font-family: monospace; font-size: 16px; margin: 15px 0; }}
            .footer {{ background: #f8fafc; text-align: center; padding: 16px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <h2 style="margin:0;">Portal Fake Soluções Digitais</h2>
              <p style="margin:5px 0 0 0; opacity:0.9;">Setor de Atendimento ao Cliente</p>
            </div>
            <div class="content">
              <div class="badge">⚠ PENDÊNCIA DOCUMENTAL IDENTIFICADA</div>
              <h3>Olá, {nome_cliente}!</h3>
              <p>Identificamos pendências no envio da sua documentação. Para darmos continuidade ao seu cadastro, solicitamos o reenvio dos itens apontados abaixo:</p>
              
              <div class="alert-box">
                <strong style="color:#b91c1c;">Documento(s) Faltante(s) ou Incompletos:</strong>
                <ul style="margin-top:10px; padding-left:20px;">
                  {itens_html}
                </ul>
              </div>

              <div class="protocolo">
                <strong>Protocolo de Acompanhamento:</strong> {protocolo}
              </div>

              <p><strong>Instruções de Reenvio:</strong></p>
              <p>Por favor, responda a este e-mail anexando os documentos faltantes atualizados em formato PDF.</p>
              <p>Atenciosamente,<br>Equipe de Atendimento - Portal Fake</p>
            </div>
            <div class="footer">
              Portal Fake Soluções Digitais &copy; 2026 - Todos os direitos reservados.
            </div>
          </div>
        </body>
        </html>
        """

    def enviar_resposta_cliente(
        self,
        email_destino: str,
        aprovado: bool,
        protocolo: str,
        pendencias: Optional[List[str]] = None,
        dados_cliente: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Envia e-mail em HTML responsivo corporativo via SMTP SSL."""
        pendencias = pendencias or []
        dados_cliente = dados_cliente or {}
        nome_cliente = dados_cliente.get("nome", "Prezado(a) Cliente")

        assunto = (
            f"[Portal Fake] Cadastro Aprovado e Ativado - Protocolo {protocolo}"
            if aprovado
            else f"[Portal Fake] Ação Necessária: Pendência na Documentação - Protocolo {protocolo}"
        )

        html_corpo = (
            self._gerar_html_sucesso(nome_cliente, protocolo)
            if aprovado
            else self._gerar_html_pendencia(nome_cliente, protocolo, pendencias)
        )

        if not self.email_remetente or not self.senha_app:
            logger.warning(
                f"[RESPOSTA CLIENTE] Credenciais SMTP não configuradas. "
                f"Simulando envio de e-mail ({'APROVADO' if aprovado else 'PENDENTE'}) para {email_destino} | Assunto: {assunto}"
            )
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = self.email_remetente
        msg["To"] = email_destino
        msg.attach(MIMEText(html_corpo, "html", "utf-8"))

        try:
            logger.info(f"[RESPOSTA CLIENTE] Conectando ao servidor SMTP {self.host}:{self.port}...")
            with smtplib.SMTP_SSL(self.host, self.port) as server:
                server.login(self.email_remetente, self.senha_app)
                server.sendmail(self.email_remetente, email_destino, msg.as_string())

            logger.info(f"[RESPOSTA CLIENTE] E-mail transacional enviado com sucesso para {email_destino}.")
            return True

        except Exception as erro:
            logger.error(f"[RESPOSTA CLIENTE] Erro ao enviar e-mail via SMTP: {erro}")
            return False
