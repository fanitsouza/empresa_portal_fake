import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from processo_1_envio_fichas import executar_processo_1

def executar_orquestracao(modo="unico", row_index=0, registro=None):
    """
    Atalho de compatibilidade para o Processo 1 - Envio de Fichas para Assinatura.
    Dica: Para o painel unificado com todos os processos, use: python main.py
    """
    param = registro if registro is not None else row_index
    return executar_processo_1(registro=param, modo=modo)

if __name__ == "__main__":
    executar_orquestracao(modo="unico", row_index=0)

