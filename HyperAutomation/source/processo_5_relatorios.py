from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


PATH_ROOT = Path(__file__).resolve().parent.parent
DIRETORIO_RELATORIOS_PADRAO = PATH_ROOT / "resources" / "Relatorios"
LOGGER = logging.getLogger("PROCESSO_5_RELATORIOS")


def configurar_logs() -> None:
    """Configura logging de console sem criar arquivos automaticamente."""
    if LOGGER.handlers:
        return
    LOGGER.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    LOGGER.addHandler(handler)
    LOGGER.propagate = False


def gerar_versao_relatorio() -> str:
    agora = datetime.now().strftime("%Y%m%d-%H%M%S")
    sufixo = uuid4().hex[:4].upper()
    return f"RELATORIO-{agora}-{sufixo}"


def mascarar_cpf(cpf: Any) -> str:
    digitos = re.sub(r"\D", "", "" if cpf is None else str(cpf))
    if len(digitos) != 11:
        return "CPF_INVALIDO"
    return f"***.***.***-{digitos[-2:]}"


def _inteiro_nao_negativo(valor: Any) -> int:
    try:
        return max(0, int(valor))
    except (TypeError, ValueError):
        return 0


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _motivo_seguro(valor: Any, padrao: str) -> str:
    texto = _texto(valor)
    if not texto:
        return padrao

    texto_baixo = texto.casefold()
    termos_sensiveis = (
        "http://",
        "https://",
        "token",
        "senha",
        "password",
        "traceback",
        "stack trace",
    )
    if any(termo in texto_baixo for termo in termos_sensiveis):
        return padrao

    return texto[:180]


def _resultados_sac(resultado_sac: Any) -> list[dict[str, Any]]:
    if not isinstance(resultado_sac, dict):
        return []
    resultados = resultado_sac.get("resultados")
    if not isinstance(resultados, list):
        return []
    return [item for item in resultados if isinstance(item, dict)]


def calcular_metricas(resultado_sac: Any) -> dict[str, int | float]:
    resultados = _resultados_sac(resultado_sac)
    resultado_dict = resultado_sac if isinstance(resultado_sac, dict) else {}

    if resultados:
        total_atendido = len(resultados)
        cadastros_sucesso = sum(
            1 for item in resultados if item.get("cadastro", {}).get("sucesso") is True
        )
        cadastros_erro = total_atendido - cadastros_sucesso
        comunicacoes_enviadas = sum(
            1 for item in resultados if item.get("sac", {}).get("comunicacao") == "enviada"
        )
        comunicacoes_pendentes = sum(
            1 for item in resultados if item.get("sac", {}).get("comunicacao") == "pendente"
        )
    else:
        total_atendido = _inteiro_nao_negativo(resultado_dict.get("total_atendido"))
        cadastros_sucesso = _inteiro_nao_negativo(resultado_dict.get("sucessos_cadastro"))
        cadastros_erro = _inteiro_nao_negativo(resultado_dict.get("erros_cadastro"))
        comunicacoes_enviadas = _inteiro_nao_negativo(
            resultado_dict.get("comunicacoes_enviadas")
        )
        comunicacoes_pendentes = _inteiro_nao_negativo(
            resultado_dict.get("comunicacoes_pendentes")
        )

    sucessos_api = sum(
        1
        for item in resultados
        if item.get("cadastro", {}).get("sucesso") is True
        and _texto(item.get("cadastro", {}).get("metodo")).casefold() == "api"
    )
    sucessos_rpa = sum(
        1
        for item in resultados
        if item.get("cadastro", {}).get("sucesso") is True
        and _texto(item.get("cadastro", {}).get("metodo")).casefold() == "rpa"
    )

    taxa_sucesso = (cadastros_sucesso / total_atendido) if total_atendido else 0.0
    taxa_erro = (cadastros_erro / total_atendido) if total_atendido else 0.0

    return {
        "total_atendido": total_atendido,
        "cadastros_sucesso": cadastros_sucesso,
        "cadastros_erro": cadastros_erro,
        "comunicacoes_enviadas": comunicacoes_enviadas,
        "comunicacoes_pendentes": comunicacoes_pendentes,
        "sucessos_api": sucessos_api,
        "sucessos_rpa": sucessos_rpa,
        "taxa_sucesso": round(taxa_sucesso, 4),
        "taxa_erro": round(taxa_erro, 4),
    }


def montar_ocorrencias(resultado_sac: Any) -> list[dict[str, Any]]:
    ocorrencias: list[dict[str, Any]] = []

    for item in _resultados_sac(resultado_sac):
        cliente = item.get("cliente") if isinstance(item.get("cliente"), dict) else {}
        cadastro = item.get("cadastro") if isinstance(item.get("cadastro"), dict) else {}
        sac = item.get("sac") if isinstance(item.get("sac"), dict) else {}

        base = {
            "protocolo": _texto(sac.get("protocolo")),
            "cpf_mascarado": mascarar_cpf(cliente.get("cpf")),
            "metodo": _texto(cadastro.get("metodo")) or "indefinido",
        }

        if cadastro.get("sucesso") is not True:
            ocorrencias.append(
                {
                    **base,
                    "tipo": "cadastro_nao_concluido",
                    "status": _texto(cadastro.get("status")),
                    "motivo": _motivo_seguro(
                        cadastro.get("erro"), "Cadastro nao concluido."
                    ),
                }
            )

        if sac.get("comunicacao") == "pendente":
            ocorrencias.append(
                {
                    **base,
                    "tipo": "comunicacao_pendente",
                    "status": "pendente",
                    "motivo": _motivo_seguro(
                        sac.get("erro_envio"), "Comunicacao pendente."
                    ),
                }
            )

        if "arquivo_registro" in sac and not sac.get("arquivo_registro"):
            ocorrencias.append(
                {
                    **base,
                    "tipo": "registro_sac_nao_persistido",
                    "status": "pendente",
                    "motivo": "Registro SAC nao persistido.",
                }
            )

    return ocorrencias


def _falhas_por_tipo(ocorrencias: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(_texto(item.get("tipo")) for item in ocorrencias if item.get("tipo")))


def registrar_relatorio(
    relatorio: dict[str, Any], diretorio_relatorios: str | Path
) -> Path:
    diretorio = Path(diretorio_relatorios).expanduser().resolve()
    diretorio.mkdir(parents=True, exist_ok=True)

    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", relatorio["versao"])
    caminho = diretorio / f"{nome_seguro}.json"
    relatorio["arquivo_relatorio"] = str(caminho)
    caminho.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return caminho


def executar_processo_5(
    resultado_sac: Any, diretorio_relatorios: str | Path | None = None
) -> dict[str, Any]:
    """Gera relatorio gerencial a partir do contrato do Processo 4 SAC."""
    configurar_logs()
    diretorio = diretorio_relatorios or DIRETORIO_RELATORIOS_PADRAO

    LOGGER.info("Inicio do Processo 5 Relatorios.")
    metricas = calcular_metricas(resultado_sac)
    ocorrencias = montar_ocorrencias(resultado_sac)
    LOGGER.info(
        "Metricas calculadas: total=%s, sucesso=%s, erro=%s, ocorrencias=%s.",
        metricas["total_atendido"],
        metricas["cadastros_sucesso"],
        metricas["cadastros_erro"],
        len(ocorrencias),
    )

    relatorio = {
        "versao": gerar_versao_relatorio(),
        "gerado_em": datetime.now().astimezone().isoformat(),
        "metricas": metricas,
        "ocorrencias": ocorrencias,
        "falhas_por_tipo": _falhas_por_tipo(ocorrencias),
        "arquivo_relatorio": None,
    }

    try:
        caminho = registrar_relatorio(relatorio, diretorio)
        LOGGER.info("Relatorio criado em %s.", caminho)
    except Exception as erro:  # noqa: BLE001 - metricas em memoria devem sobreviver
        relatorio["arquivo_relatorio"] = None
        LOGGER.error("Falha ao persistir relatorio: %s", erro)

    LOGGER.info("Fim do Processo 5 Relatorios.")
    return relatorio
