import argparse
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

import typing
from dotenv import load_dotenv

try:
    from playwright.sync_api import Locator, Page, TimeoutError, sync_playwright
except ImportError:
    Locator = typing.Any  # type: ignore
    Page = typing.Any  # type: ignore
    TimeoutError = Exception  # type: ignore
    sync_playwright = None  # type: ignore



BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent
PATH_ROOT = SOURCE_DIR.parent
ENV_PATH = SOURCE_DIR / ".env"
BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data"
GMAIL_BROWSER_DATA_DIR = PATH_ROOT / "resources" / "browser_data_gmail"
DOWNLOADS_DIR = PATH_ROOT / "downloads" / "gmail"
EVIDENCIAS_DIR = PATH_ROOT / "evidencias" / "gmail"

load_dotenv(ENV_PATH)

GMAIL_URL = os.getenv("GMAIL_URL", "https://mail.google.com/mail/u/0/#inbox")
GMAIL_TERMO_BUSCA_PADRAO = os.getenv("GMAIL_TERMO_BUSCA", "has:attachment")


SEARCH_INPUT_SELECTORS = [
    "input[aria-label='Search mail']",
    "input[aria-label='Pesquisar e-mail']",
    "form[role='search'] input",
]

EMAIL_ROW_SELECTORS = [
    "tr[role='link']",
    "div[role='main'] tr",
]

DOWNLOAD_BUTTON_SELECTORS = [
    "[aria-label*='Download attachment']",
    "[aria-label*='Download all attachments']",
    "[aria-label*='Download']",
    "[aria-label*='Fazer download do anexo']",
    "[aria-label*='Fazer o download de todos os anexos']",
    "[aria-label*='Fazer download']",
    "[aria-label*='Baixar anexo']",
    "[data-tooltip*='Download']",
    "[data-tooltip*='Fazer download']",
    "[data-tooltip*='Baixar']",
    "[download]",
]

ATTACHMENT_HOVER_SELECTORS = [
    "[download_url]",
    "[aria-label*='Attachment']",
    "[aria-label*='Anexo']",
    ".aQH",
    ".aZo",
]

BACK_TO_RESULTS_SELECTORS = [
    "[aria-label='Back']",
    "[aria-label='Voltar']",
    "div[role='button'][data-tooltip='Back']",
    "div[role='button'][data-tooltip='Voltar']",
]

REPLY_BUTTON_SELECTORS = [
    "div[role='button']:has-text('Responder')",
    "span:has-text('Responder')",
    "[aria-label^='Reply']",
    "[aria-label^='Responder']",
]

MESSAGE_BOX_SELECTORS = [
    "div[role='textbox'][aria-label*='Message Body']",
    "div[role='textbox'][aria-label*='Corpo da mensagem']",
    "div[role='textbox'][aria-label*='Mensagem']",
    "div[contenteditable='true'][role='textbox']",
]

SEND_BUTTON_SELECTORS = [
    "div[role='button'][aria-label*='Send']",
    "div[role='button'][aria-label*='Enviar']",
    "div[role='button']:has-text('Enviar')",
]


def primeiro_visivel(page: Page, selectors: Iterable[str], timeout_ms: int = 15000) -> Locator:
    ultimo_erro = None
    for selector in selectors:
        locator = primeiro_locator(page.locator(selector))
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except TimeoutError as erro:
            ultimo_erro = erro
    raise TimeoutError(f"Nenhum seletor ficou visivel: {list(selectors)}") from ultimo_erro


def primeiro_locator(locator: Locator) -> Locator:
    primeiro = locator.first
    return primeiro() if callable(primeiro) else primeiro


def nome_seguro(valor: str) -> str:
    valor = re.sub(r"[^\w.\- ]+", "_", valor, flags=re.UNICODE).strip()
    return valor or "anexo"


def caminho_unico(pasta: Path, nome_arquivo: str) -> Path:
    destino = pasta / nome_arquivo
    if not destino.exists():
        return destino

    base = destino.stem
    sufixo = destino.suffix
    contador = 2
    while True:
        candidato = pasta / f"{base}_{contador}{sufixo}"
        if not candidato.exists():
            return candidato
        contador += 1


def salvar_screenshot_email(page: Page, pasta_evidencias: Path, indice_email: int) -> Path:
    pasta_evidencias.mkdir(parents=True, exist_ok=True)
    destino = caminho_unico(pasta_evidencias, f"email_{indice_email + 1:03d}.png")
    page.screenshot(path=str(destino), full_page=True)
    print(f"[Gmail] Evidencia salva: {destino}")
    return destino


def dados_download_url(valor: str) -> tuple[str, str] | None:
    partes = valor.split(":", 2)
    if len(partes) != 3:
        return None

    nome_arquivo = nome_seguro(unquote(partes[1]))
    url = partes[2]
    if not url.startswith(("http://", "https://")):
        return None

    return nome_arquivo, url


def abrir_gmail(page: Page) -> None:
    print("[Gmail] Abrindo caixa de entrada...")
    page.goto(GMAIL_URL, wait_until="domcontentloaded")
    try:
        primeiro_visivel(page, SEARCH_INPUT_SELECTORS, timeout_ms=20000)
    except TimeoutError:
        print(
            "[Gmail] Faca login manualmente na janela aberta. "
            "O robo continua assim que a caixa de entrada carregar."
        )
        primeiro_visivel(page, SEARCH_INPUT_SELECTORS, timeout_ms=180000)


def pesquisar_email(page: Page, termo_busca: str) -> None:
    print(f"[Gmail] Pesquisando email por: {termo_busca}")
    caixa_pesquisa = primeiro_visivel(page, SEARCH_INPUT_SELECTORS)
    caixa_pesquisa.fill(termo_busca)
    caixa_pesquisa.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2500)


def linhas_de_email(page: Page) -> Locator:
    for selector in EMAIL_ROW_SELECTORS:
        linhas = page.locator(selector)
        try:
            primeiro_locator(linhas).wait_for(state="visible", timeout=10000)
            return linhas
        except TimeoutError:
            continue
    raise RuntimeError("Nenhum email encontrado para a busca informada.")


def abrir_email_por_indice(page: Page, indice: int) -> None:
    linhas = linhas_de_email(page)
    total = linhas.count()
    if indice >= total:
        raise RuntimeError(f"Email de indice {indice} nao encontrado. Total visivel: {total}.")

    print(f"[Gmail] Abrindo email {indice + 1}/{total}...")
    linha = linhas.nth(indice)
    linha.scroll_into_view_if_needed(timeout=5000)
    clicar_area_segura_da_linha(linha)
    aguardar_conversa_aberta(page)


def clicar_area_segura_da_linha(linha: Locator) -> None:
    box = linha.bounding_box(timeout=5000)
    if not box:
        linha.click()
        return

    # O centro da linha do Gmail pode ficar sobre chips de anexo.
    # Clicar no primeiro terco evita abrir o PDF/arquivo anexado por engano.
    x_seguro = min(max(box["width"] * 0.28, 180), max(box["width"] - 40, 10))
    y_seguro = max(box["height"] / 2, 8)
    linha.click(position={"x": x_seguro, "y": y_seguro})


def aguardar_conversa_aberta(page: Page) -> None:
    try:
        primeiro_visivel(
            page,
            [
                "div[role='main'] h2",
                "div[role='main'] [data-message-id]",
                "div[role='main'] .adn",
            ],
            timeout_ms=8000,
        )
        page.wait_for_timeout(1000)
    except TimeoutError as erro:
        raise RuntimeError(
            "Nao consegui confirmar que o email foi aberto. "
            "O Gmail pode ter clicado em um anexo ou outro item da linha."
        ) from erro


def voltar_para_resultados(page: Page) -> None:
    for selector in BACK_TO_RESULTS_SELECTORS:
        botao = page.locator(selector).first
        botao = botao() if callable(botao) else botao
        try:
            botao.wait_for(state="visible", timeout=3000)
            botao.click()
            primeiro_locator(linhas_de_email(page)).wait_for(state="visible", timeout=10000)
            page.wait_for_timeout(1000)
            return
        except TimeoutError:
            continue

    page.go_back(wait_until="domcontentloaded")
    primeiro_locator(linhas_de_email(page)).wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)


def preparar_anexos_para_download(page: Page) -> None:
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(500)
    for selector in ATTACHMENT_HOVER_SELECTORS:
        itens = page.locator(selector)
        total = itens.count()
        for indice in range(total):
            item = itens.nth(indice)
            try:
                if item.is_visible():
                    item.scroll_into_view_if_needed(timeout=3000)
                    item.hover(timeout=3000)
                    page.wait_for_timeout(300)
            except TimeoutError:
                continue


def baixar_anexos(page: Page, pasta_downloads: Path, falhar_sem_anexo: bool = False) -> list[Path]:
    pasta_downloads.mkdir(parents=True, exist_ok=True)
    arquivos_baixados: list[Path] = []
    vistos: set[str] = set()

    print("[Gmail] Procurando anexos para baixar...")
    preparar_anexos_para_download(page)
    arquivos_baixados.extend(baixar_anexos_por_download_url(page, pasta_downloads, vistos))

    for selector in DOWNLOAD_BUTTON_SELECTORS:
        botoes = page.locator(selector)
        total = botoes.count()
        for indice in range(total):
            botao = botoes.nth(indice)
            if not botao.is_visible():
                continue

            chave = f"{selector}:{indice}"
            if chave in vistos:
                continue
            vistos.add(chave)

            try:
                with page.expect_download(timeout=15000) as download_info:
                    botao.click()
                download = download_info.value
                nome_arquivo = nome_seguro(download.suggested_filename)
                destino = caminho_unico(pasta_downloads, nome_arquivo)
                download.save_as(str(destino))
                arquivos_baixados.append(destino)
                print(f"[Gmail] Anexo baixado: {destino}")
            except TimeoutError:
                continue

    if falhar_sem_anexo and not arquivos_baixados:
        raise RuntimeError("Email encontrado, mas nenhum anexo foi baixado.")

    return arquivos_baixados


def baixar_anexos_por_download_url(page: Page, pasta_downloads: Path, vistos: set[str]) -> list[Path]:
    arquivos_baixados: list[Path] = []
    anexos = page.locator("[download_url]")
    total = anexos.count()

    for indice in range(total):
        valor = anexos.nth(indice).get_attribute("download_url")
        if not valor or valor in vistos:
            continue

        vistos.add(valor)
        dados = dados_download_url(valor)
        if not dados:
            continue

        nome_arquivo, url = dados
        try:
            resposta = page.context.request.get(url, timeout=30000)
            if not resposta.ok:
                print(f"[Gmail] Falha ao baixar {nome_arquivo}: HTTP {resposta.status}")
                continue

            destino = caminho_unico(pasta_downloads, nome_arquivo)
            destino.write_bytes(resposta.body())
            arquivos_baixados.append(destino)
            print(f"[Gmail] Anexo baixado: {destino}")
        except Exception as erro:
            print(f"[Gmail] Falha ao baixar {nome_arquivo}: {erro}")

    return arquivos_baixados


def extrair_remetente_email(page: Page) -> tuple[str, str]:
    """Retorna (nome_cliente, email_cliente) da conversa aberta no Gmail."""
    try:
        elem_remetente = page.locator("span.gD").first
        if elem_remetente.is_visible(timeout=3000):
            nome = elem_remetente.inner_text().strip() or "Cliente"
            email = elem_remetente.get_attribute("email") or "cliente@example.com"
            return nome, email
    except Exception:
        pass
    return "Cliente", "cliente@example.com"


def processar_emails_resultado(
    page: Page,
    pasta_downloads: Path,
    pasta_evidencias: Path,
    mensagem_padrao: str,
    enviar_resposta: bool,
    limite: int,
) -> list[Path]:
    from atendimento.config import Configuracao
    from atendimento.modelos import Solicitacao
    from atendimento.orquestrador import OrquestradorAtendimento

    config = Configuracao.criar()
    orquestrador = OrquestradorAtendimento(config)

    total_visivel = linhas_de_email(page).count()
    total_processar = total_visivel if limite <= 0 else min(limite, total_visivel)

    if total_processar == 0:
        raise RuntimeError("Nenhum email encontrado para a busca informada.")

    print(f"[Gmail] {total_processar} email(s) serao processados.")
    todos_arquivos: list[Path] = []

    for indice in range(total_processar):
        abrir_email_por_indice(page, indice)
        try:
            salvar_screenshot_email(page, pasta_evidencias, indice)
            protocolo = f"SOL-{indice + 1:03d}"
            pasta_email_downloads = pasta_downloads / protocolo
            arquivos = baixar_anexos(page, pasta_email_downloads, falhar_sem_anexo=False)
            todos_arquivos.extend(arquivos)

            if arquivos:
                nome_cliente, email_cliente = extrair_remetente_email(page)
                solicitacao = Solicitacao(
                    protocolo=protocolo,
                    nome_cliente=nome_cliente,
                    email_cliente=email_cliente,
                    cpf="",
                    anexos=arquivos,
                )
                resultado = orquestrador.processar(solicitacao)
                print(f"[Orquestrador] Protocolo {protocolo} processado. Status: {resultado.status.value}")

                if enviar_resposta:
                    texto_resposta = resultado.arquivo_resposta.read_text(encoding="utf-8")
                    responder_recebimento(page, texto_resposta)
            else:
                print("[Gmail] Nenhum anexo baixado neste email. Indo para o proximo.")
        finally:
            voltar_para_resultados(page)

    if not todos_arquivos:
        raise RuntimeError("Nenhum anexo foi baixado dos emails encontrados.")

    return todos_arquivos


def responder_recebimento(page: Page, mensagem: str) -> None:
    print("[Gmail] Enviando resposta de recebimento...")
    botao_responder = primeiro_visivel(page, REPLY_BUTTON_SELECTORS, timeout_ms=15000)
    botao_responder.click()
    caixa_mensagem = primeiro_visivel(page, MESSAGE_BOX_SELECTORS, timeout_ms=15000)
    caixa_mensagem.fill(mensagem)
    botao_enviar = primeiro_visivel(page, SEND_BUTTON_SELECTORS, timeout_ms=15000)
    botao_enviar.click()
    page.wait_for_timeout(2500)


def executar(
    termo_busca: str,
    mensagem: str,
    enviar_resposta: bool,
    headless: bool,
    browser_channel: str,
    limite: int,
) -> list[Path]:
    if sync_playwright is None:
        raise RuntimeError("O pacote 'playwright' não está instalado. Instale com: pip install playwright && playwright install chrome")

    with sync_playwright() as p:
        launch_options = {
            "user_data_dir": str(GMAIL_BROWSER_DATA_DIR),
            "headless": headless,
            "accept_downloads": True,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if browser_channel != "chromium":
            launch_options["channel"] = browser_channel

        try:
            context = p.chromium.launch_persistent_context(**launch_options)
        except Exception as erro:
            if browser_channel == "chromium":
                raise
            print(
                f"[Gmail] Nao consegui abrir o navegador '{browser_channel}': {erro}\n"
                "[Gmail] Tentando com o Chromium padrao do Playwright..."
            )
            launch_options.pop("channel", None)
            launch_options["user_data_dir"] = str(BROWSER_DATA_DIR)
            context = p.chromium.launch_persistent_context(**launch_options)

        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()
        try:
            abrir_gmail(page)
            pesquisar_email(page, termo_busca)
            return processar_emails_resultado(
                page=page,
                pasta_downloads=DOWNLOADS_DIR,
                pasta_evidencias=EVIDENCIAS_DIR,
                mensagem=mensagem,
                enviar_resposta=enviar_resposta,
                limite=limite,
            )
        finally:
            context.close()


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Busca um email no Gmail, baixa anexos e envia resposta de recebimento."
    )
    parser.add_argument(
        "--busca",
        default=GMAIL_TERMO_BUSCA_PADRAO,
        help="Termo de busca do Gmail. Ex: \"from:cliente@email.com has:attachment\" ou um nome.",
    )
    parser.add_argument(
        "--mensagem",
        default=os.getenv(
            "GMAIL_MENSAGEM_RECEBIMENTO",
            "Ola! Confirmamos o recebimento do seu email e dos documentos anexados. Obrigado.",
        ),
        help="Mensagem enviada como resposta de recebimento.",
    )
    parser.add_argument(
        "--no-reply",
        action="store_true",
        help="Baixa os anexos, mas nao envia resposta no email.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa sem janela visivel. Use apenas depois que o login ja estiver salvo.",
    )
    parser.add_argument(
        "--browser",
        default=os.getenv("GMAIL_BROWSER", "chrome"),
        choices=["chrome", "msedge", "chromium"],
        help="Navegador usado pelo Playwright. Para Gmail, prefira chrome.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=int(os.getenv("GMAIL_LIMITE_EMAILS", "0")),
        help="Quantidade maxima de emails da lista para processar. Use 0 para todos os visiveis.",
    )
    return parser


if __name__ == "__main__":
    argumentos = criar_parser().parse_args()

    anexos = executar(
        termo_busca=argumentos.busca,
        mensagem=argumentos.mensagem,
        enviar_resposta=not argumentos.no_reply,
        headless=argumentos.headless,
        browser_channel=argumentos.browser,
        limite=argumentos.limite,
    )

    print("\nProcesso finalizado com sucesso.")
    print("Arquivos baixados:")
    for anexo in anexos:
        print(f"- {anexo}")
