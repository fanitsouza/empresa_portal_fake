import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger("PORTAL_INTEGRAÇÃO")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    sync_playwright = None  # type: ignore


class PortalERPIntegracao:
    """Automação Web RPA para cadastro de clientes no ERP Simulado via Playwright."""

    def __init__(self, raiz_projeto: Path | None = None) -> None:
        if raiz_projeto is None:
            raiz_projeto = Path(__file__).resolve().parents[2]

        self.raiz_projeto = raiz_projeto
        self.portal_html = raiz_projeto / "resources" / "portal_fake" / "index.html"
        self.pasta_screenshots = raiz_projeto / "resources" / "screenshots"
        self.pasta_screenshots.mkdir(parents=True, exist_ok=True)

    def cadastrar_cliente_erp(
        self, dados_cliente: Dict[str, str], headless: bool = True
    ) -> bool:
        """
        Acessa o Portal ERP local, preenche o formulário de cadastro com os dados extraídos,
        salva evidências em screenshot e confirma o cadastro.
        """
        logger.info(f"[PORTAL INTEGRAÇÃO] Iniciando cadastro ERP para: {dados_cliente.get('nome')}")

        if not self.portal_html.exists():
            logger.error(f"[PORTAL INTEGRAÇÃO] Arquivo index.html do portal não encontrado em: {self.portal_html}")
            return False

        url_portal = self.portal_html.as_uri()

        if not HAS_PLAYWRIGHT or sync_playwright is None:
            logger.warning(
                "[PORTAL INTEGRAÇÃO] Playwright não está instalado no ambiente Python. "
                "Executando simulação de cadastro ERP com registro de evidência em log."
            )
            logger.info(f"[PORTAL INTEGRAÇÃO] [SIMULAÇÃO] Cliente {dados_cliente.get('nome')} registrado como ATIVO.")
            return True

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                page = browser.new_page()

                logger.info(f"[PORTAL INTEGRAÇÃO] Navegando para o Portal ERP: {url_portal}")
                page.goto(url_portal)
                page.wait_for_selector("#btnNovo", state="visible")

                # Clica em Novo Cadastro para abrir o modal
                page.click("#btnNovo")
                page.wait_for_selector("#modal", state="visible")

                # Separa Nome e Sobrenome
                nome_completo = dados_cliente.get("nome", "Cliente Demonstração").strip()
                partes_nome = nome_completo.split(" ", 1)
                primeiro_nome = partes_nome[0]
                sobrenome = partes_nome[1] if len(partes_nome) > 1 else "Silva"

                cpf = dados_cliente.get("cpf", "12345678900")
                email = dados_cliente.get("email", "cliente@example.com")

                # Preenchimento dos campos do formulário
                page.fill("#f_nome", primeiro_nome)
                page.fill("#f_sobrenome", sobrenome)
                page.fill("#f_cpf", cpf[:11])
                page.fill("#f_email", email)
                page.select_option("#f_status", "ATIVO")
                page.fill("#f_observacao", "Cadastro automatizado pelo Robô de Atendimento Processo 1")

                # Evidência 1: Formulário preenchido
                screenshot_01 = self.pasta_screenshots / "01_portal_preenchido.png"
                page.screenshot(path=str(screenshot_01), full_page=True)
                logger.info(f"[PORTAL INTEGRAÇÃO] Evidência 1 salva: {screenshot_01.name}")

                # Submete o formulário
                page.click("#btnSalvar")

                # Aguarda o fechamento do modal e atualização dos resultados
                page.wait_for_selector("#modal", state="hidden", timeout=5000)
                page.wait_for_timeout(1000)

                # Evidência 2: Cadastro confirmado na tabela
                screenshot_02 = self.pasta_screenshots / "02_extracao_dados.png"
                page.screenshot(path=str(screenshot_02), full_page=True)
                logger.info(f"[PORTAL INTEGRAÇÃO] Evidência 2 salva: {screenshot_02.name}")

                browser.close()
                logger.info(f"[PORTAL INTEGRAÇÃO] Cadastro concluído e ativado no ERP com sucesso.")
                return True

        except Exception as erro:
            logger.error(f"[PORTAL INTEGRAÇÃO] Falha ao executar automação Playwright no ERP: {erro}")
            return False
