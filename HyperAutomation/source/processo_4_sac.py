"""
Processo 4 / SAC - Atalho para processo_sac.py
Portal Fake Soluções Digitais - Hyperautomation
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from processo_sac import executar_processo_sac, main

if __name__ == "__main__":
    main()
