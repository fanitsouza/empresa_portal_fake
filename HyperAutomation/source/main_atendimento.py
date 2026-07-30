import argparse
import sys
from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao
from atendimento.orquestrador import OrquestradorAtendimento


def criar_exemplo(config: Configuracao) -> Solicitacao:
    """Cria arquivos fictícios para demonstrar o fluxo local de validação."""
    pasta = config.caixa_entrada / "solicitacao_001"
    pasta.mkdir(parents=True, exist_ok=True)

    arquivos_exemplo = {
        "ficha_cadastro_12345678900.pdf": b"conteudo ficticio da ficha",
        "rg_12345678900.jpg": b"imagem ficticia do documento",
        "comprovante_residencia_12345678900.pdf": b"comprovante ficticio",
    }

    for nome, conteudo in arquivos_exemplo.items():
        caminho = pasta / nome
        if not caminho.exists():
            caminho.write_bytes(conteudo)

    return Solicitacao(
        protocolo="SOL-001",
        nome_cliente="Cliente Demonstração",
        email_cliente="cliente@example.com",
        cpf="12345678900",
        anexos=list(pasta.iterdir()),
    )


def executar_simulacao() -> None:
    print("\n--- Executando em Modo Simulação ---")
    config = Configuracao.criar()
    solicitacao = criar_exemplo(config)
    resultado = OrquestradorAtendimento(config).processar(solicitacao)

    print("=" * 60)
    print(f"Protocolo: {resultado.protocolo}")
    print(f"Status: {resultado.status.value}")
    print(f"Destino: {resultado.pasta_destino}")
    print(f"Resposta: {resultado.arquivo_resposta}")
    print("=" * 60)

    if resultado.pendencias:
        print("Pendências:")
        for pendencia in resultado.pendencias:
            print(f"- {pendencia}")
    else:
        print("Documentação completa. Solicitação pronta para encaminhamento.")


def executar_real(args: argparse.Namespace) -> None:
    print("\n--- Executando em Modo Real (Gmail + Playwright) ---")
    from atendimento.gmail_recebimento import executar

    anexos = executar(
        termo_busca=args.busca,
        mensagem="",
        enviar_resposta=not args.no_reply,
        headless=args.headless,
        browser_channel=args.browser,
        limite=args.limite,
    )

    print("\nProcesso finalizado com sucesso.")
    print("Arquivos baixados e processados:")
    for anexo in anexos:
        print(f"- {anexo}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automação do Setor de Atendimento - Portal Fake Soluções Digitais")
    parser.add_argument(
        "--modo",
        choices=["simulacao", "real"],
        default="simulacao",
        help="Modo de execução: 'simulacao' (dados locais) ou 'real' (automação do Gmail).",
    )
    parser.add_argument(
        "--busca",
        default="has:attachment",
        help="Termo de busca no Gmail (no modo real). Ex: 'has:attachment' ou 'from:cliente@email.com'.",
    )
    parser.add_argument(
        "--no-reply",
        action="store_true",
        help="Desativa o envio automático de resposta por e-mail.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o navegador em segundo plano (sem janela visível).",
    )
    parser.add_argument(
        "--browser",
        default="chrome",
        choices=["chrome", "msedge", "chromium"],
        help="Navegador a utilizar no Playwright.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="Limite de e-mails a processar (0 para todos os visíveis).",
    )

    args = parser.parse_args()

    if args.modo == "real":
        executar_real(args)
    else:
        executar_simulacao()


if __name__ == "__main__":
    main()

