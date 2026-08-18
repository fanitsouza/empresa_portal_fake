import json
from pathlib import Path
import sys


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import processo_5_relatorios as p5  # noqa: E402


def item_sac(
    *,
    nome="Ana",
    cpf="12345678901",
    sucesso=True,
    metodo="api",
    comunicacao="enviada",
    erro=None,
    erro_envio=None,
    protocolo="SAC-20260101-120000-ABCD",
    arquivo_registro="registro.json",
):
    return {
        "cliente": {
            "nome": nome,
            "sobrenome": "Silva",
            "cpf": cpf,
            "email": f"{nome.casefold()}@example.com",
        },
        "cadastro": {
            "sucesso": sucesso,
            "status": "cadastro_concluido" if sucesso else "cadastro_nao_concluido",
            "metodo": metodo,
            "erro": erro,
        },
        "sac": {
            "protocolo": protocolo,
            "comunicacao": comunicacao,
            "canal": "email",
            "mensagem": "Mensagem segura ao cliente.",
            "erro_envio": erro_envio,
            "registrado_em": "2026-01-01T12:00:00-04:00",
            "arquivo_registro": arquivo_registro,
        },
    }


def resultado_sac(resultados):
    sucessos = sum(1 for item in resultados if item["cadastro"]["sucesso"])
    enviadas = sum(1 for item in resultados if item["sac"]["comunicacao"] == "enviada")
    pendentes = sum(1 for item in resultados if item["sac"]["comunicacao"] == "pendente")
    return {
        "total_atendido": len(resultados),
        "sucessos_cadastro": sucessos,
        "erros_cadastro": len(resultados) - sucessos,
        "comunicacoes_enviadas": enviadas,
        "comunicacoes_pendentes": pendentes,
        "resultados": resultados,
    }


def test_lote_sucesso_calcula_metricas(tmp_path):
    relatorio = p5.executar_processo_5(
        resultado_sac([item_sac(), item_sac(nome="Bruno", metodo="rpa")]),
        diretorio_relatorios=tmp_path,
    )

    assert relatorio["metricas"]["total_atendido"] == 2
    assert relatorio["metricas"]["cadastros_sucesso"] == 2
    assert relatorio["metricas"]["cadastros_erro"] == 0
    assert relatorio["metricas"]["sucessos_api"] == 1
    assert relatorio["metricas"]["sucessos_rpa"] == 1
    assert relatorio["metricas"]["taxa_sucesso"] == 1.0


def test_lote_erro_gera_ocorrencias_sem_cpf_puro(tmp_path):
    relatorio = p5.executar_processo_5(
        resultado_sac(
            [
                item_sac(
                    sucesso=False,
                    metodo="rpa",
                    comunicacao="pendente",
                    erro="Cadastro nao concluido pelo fallback RPA.",
                    erro_envio="Cliente sem e-mail valido.",
                )
            ]
        ),
        diretorio_relatorios=tmp_path,
    )

    assert relatorio["metricas"]["cadastros_erro"] == 1
    assert len(relatorio["ocorrencias"]) == 2
    assert all("12345678901" not in json.dumps(item) for item in relatorio["ocorrencias"])


def test_lote_misto_calcula_comunicacoes_e_taxas(tmp_path):
    relatorio = p5.executar_processo_5(
        resultado_sac(
            [
                item_sac(sucesso=True, metodo="api", comunicacao="enviada"),
                item_sac(
                    nome="Bruno",
                    cpf="22233344455",
                    sucesso=False,
                    metodo="rpa",
                    comunicacao="pendente",
                    erro="Falha final.",
                    erro_envio="Servico de e-mail nao configurado.",
                ),
            ]
        ),
        diretorio_relatorios=tmp_path,
    )

    assert relatorio["metricas"]["total_atendido"] == 2
    assert relatorio["metricas"]["cadastros_sucesso"] == 1
    assert relatorio["metricas"]["cadastros_erro"] == 1
    assert relatorio["metricas"]["comunicacoes_enviadas"] == 1
    assert relatorio["metricas"]["comunicacoes_pendentes"] == 1
    assert relatorio["metricas"]["taxa_sucesso"] == 0.5
    assert relatorio["metricas"]["taxa_erro"] == 0.5


def test_lote_vazio_nao_divide_por_zero(tmp_path):
    relatorio = p5.executar_processo_5(resultado_sac([]), diretorio_relatorios=tmp_path)

    assert relatorio["metricas"]["total_atendido"] == 0
    assert relatorio["metricas"]["taxa_sucesso"] == 0.0
    assert relatorio["metricas"]["taxa_erro"] == 0.0
    assert relatorio["ocorrencias"] == []


def test_resultado_sac_invalido_e_tratado_como_vazio(tmp_path):
    relatorio = p5.executar_processo_5(None, diretorio_relatorios=tmp_path)

    assert relatorio["metricas"]["total_atendido"] == 0
    assert relatorio["arquivo_relatorio"] is not None


def test_relatorio_json_e_criado_com_utf8(tmp_path):
    relatorio = p5.executar_processo_5(
        resultado_sac([item_sac(nome="Joao")]), diretorio_relatorios=tmp_path
    )

    arquivo = Path(relatorio["arquivo_relatorio"])
    assert arquivo.is_file()
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["versao"] == relatorio["versao"]
    assert dados["metricas"]["total_atendido"] == 1


def test_versoes_diferentes_nao_sobrescrevem_relatorios(tmp_path):
    primeiro = p5.executar_processo_5(resultado_sac([]), diretorio_relatorios=tmp_path)
    segundo = p5.executar_processo_5(resultado_sac([]), diretorio_relatorios=tmp_path)

    assert primeiro["versao"] != segundo["versao"]
    assert primeiro["arquivo_relatorio"] != segundo["arquivo_relatorio"]
    assert Path(primeiro["arquivo_relatorio"]).is_file()
    assert Path(segundo["arquivo_relatorio"]).is_file()


def test_retorno_estruturado_contem_chaves_principais(tmp_path):
    relatorio = p5.executar_processo_5(resultado_sac([]), diretorio_relatorios=tmp_path)

    assert set(relatorio) == {
        "versao",
        "gerado_em",
        "metricas",
        "ocorrencias",
        "falhas_por_tipo",
        "arquivo_relatorio",
    }
    assert set(relatorio["metricas"]) == {
        "total_atendido",
        "cadastros_sucesso",
        "cadastros_erro",
        "comunicacoes_enviadas",
        "comunicacoes_pendentes",
        "sucessos_api",
        "sucessos_rpa",
        "taxa_sucesso",
        "taxa_erro",
    }


def test_falha_de_persistencia_mantem_metricas_em_memoria(tmp_path, monkeypatch):
    def registrar_com_falha(_relatorio, _diretorio):
        raise OSError("falha controlada")

    monkeypatch.setattr(p5, "registrar_relatorio", registrar_com_falha)

    relatorio = p5.executar_processo_5(
        resultado_sac([item_sac()]), diretorio_relatorios=tmp_path
    )

    assert relatorio["metricas"]["total_atendido"] == 1
    assert relatorio["metricas"]["cadastros_sucesso"] == 1
    assert relatorio["arquivo_relatorio"] is None


def test_motivos_sensiveis_sao_generalizados(tmp_path):
    relatorio = p5.executar_processo_5(
        resultado_sac(
            [
                item_sac(
                    sucesso=False,
                    erro="Falha em https://api.example.test?token=segredo",
                    comunicacao="pendente",
                    erro_envio="Traceback com detalhe interno",
                )
            ]
        ),
        diretorio_relatorios=tmp_path,
    )

    motivos = [item["motivo"] for item in relatorio["ocorrencias"]]
    assert "Falha em https://api.example.test?token=segredo" not in motivos
    assert "Traceback com detalhe interno" not in motivos


def test_usa_contadores_agregados_quando_nao_ha_resultados_detalhados(tmp_path):
    relatorio = p5.executar_processo_5(
        {
            "total_atendido": 3,
            "sucessos_cadastro": 2,
            "erros_cadastro": 1,
            "comunicacoes_enviadas": 1,
            "comunicacoes_pendentes": 2,
            "resultados": [],
        },
        diretorio_relatorios=tmp_path,
    )

    assert relatorio["metricas"]["total_atendido"] == 3
    assert relatorio["metricas"]["taxa_sucesso"] == 0.6667
    assert relatorio["metricas"]["taxa_erro"] == 0.3333
