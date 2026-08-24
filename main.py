#!/usr/bin/env python3
"""
Atalho principal para execução dos processos de Hyperautomation.
Redireciona para HyperAutomation/main.py
"""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
HYPER_MAIN = BASE_DIR / "HyperAutomation" / "main.py"

if __name__ == "__main__":
    if str(BASE_DIR / "HyperAutomation") not in sys.path:
        sys.path.insert(0, str(BASE_DIR / "HyperAutomation"))
    
    import runpy
    runpy.run_path(str(HYPER_MAIN), run_name="__main__")
