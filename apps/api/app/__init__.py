"""Predictions RD API."""

import sys
from pathlib import Path

__version__ = "1.0.0"

# Permite importar ``packages.games.*`` (raíz del monorepo) al ejecutar
# uvicorn desde apps/api.
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
