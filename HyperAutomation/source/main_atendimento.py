from atendimento.config import Configuracao
from atendimento.modelos import Solicitacao
from atendimento.orquestrador import OrquestradorAtendimento


def criar_exemplo(config: Configuracao) -> Solicitacao:
    """Cria arquivos fictícios para demonstrar o fluxo local."""
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


def main() -> None:
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


if __name__ == "__main__":
    main()
