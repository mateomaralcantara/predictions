"""Diagnóstico del entorno local:  npm run doctor   (o  python scripts/doctor.py)

No muestra secretos: de tu .env solo imprime los NOMBRES de las variables.
"""

from __future__ import annotations

import importlib
import os
import socket
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
OK, MAL, AVISO = "[OK]  ", "[FALLA]", "[AVISO]"
problemas: list[str] = []


def check(cond: bool, ok: str, mal: str, grave: bool = True) -> bool:
    print(f"{OK if cond else (MAL if grave else AVISO)} {ok if cond else mal}")
    if not cond and grave:
        problemas.append(mal)
    return cond


def main() -> int:
    print(f"Python {sys.version.split()[0]} en {sys.executable}")
    check(sys.version_info >= (3, 11), "Versión de Python compatible", "Se necesita Python 3.11 o superior")

    faltan = []
    for mod in (
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "jwt",
        "psycopg",
        "httpx",
        "dotenv",
        "numpy",
        "pandas",
        "bs4",
    ):
        try:
            importlib.import_module(mod)
        except Exception:  # noqa: BLE001
            faltan.append(mod)
    check(
        not faltan,
        "Dependencias de Python instaladas",
        f"Faltan módulos: {', '.join(faltan)} -> python -m pip install -r requirements-dev.txt",
    )

    for env_file in (API / ".env", ROOT / ".env"):
        if env_file.exists():
            nombres = [
                line.split("=", 1)[0].strip()
                for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
                if "=" in line and not line.strip().startswith("#") and line.split("=", 1)[1].strip()
            ]
            print(f"{AVISO} Se usa {env_file.relative_to(ROOT)} con: {', '.join(nombres) or '(vacío)'}")

    for puerto in (8000, 5174):
        with socket.socket() as s:
            libre = s.connect_ex(("127.0.0.1", puerto)) != 0
        check(
            libre,
            f"Puerto {puerto} libre",
            f"El puerto {puerto} está ocupado (¿una API o web anterior sigue abierta?)",
            grave=False,
        )

    if faltan:
        return resumen()

    sys.path[:0] = [str(ROOT), str(API)]
    os.chdir(API)
    try:
        from app.config import get_settings

        s = get_settings()
        print(
            f"{OK} Configuración cargada (entorno: {s.environment}, IA: {s.ia_proveedor or 'ninguna'}, pagos: {'sí' if s.paypal_enabled else 'no'})"
        )
        db = s.app_database_url.split("@")[-1] if "@" in s.app_database_url else s.app_database_url
        print(f"       Base de datos de la app: {db}")
        for nombre, ruta in (("Resultados", s.resultados_csv), ("Loto", s.loto_csv), ("SuperKino", s.superkino_csv)):
            check(ruta.exists(), f"CSV {nombre}: {ruta.relative_to(ROOT)}", f"No existe el CSV {nombre}: {ruta}")
    except Exception:  # noqa: BLE001
        check(False, "", "La configuración no carga:\n" + traceback.format_exc())
        return resumen()

    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as c:
            h = c.get("/api/health").json()
            check(
                h.get("sorteos", 0) > 0,
                f"API arranca: {h['sorteos']} sorteos (fuente {h['fuente_datos']})",
                "La API arranca pero no tiene datos",
            )
            r = c.get("/api/loterias/Quiniela Leidsa")
            check(
                r.status_code == 200,
                "Pantalla de lotería responde",
                f"/api/loterias/... respondió {r.status_code}: {r.text[:200]}",
            )
            r = c.post("/api/chat", json={"pregunta": "top 3 números de la nacional"})
            check(r.status_code == 200, "Asistente responde", f"/api/chat respondió {r.status_code}: {r.text[:200]}")
    except Exception:  # noqa: BLE001
        check(False, "", "La API NO arranca. Error:\n" + traceback.format_exc())
    return resumen()


def resumen() -> int:
    print()
    if problemas:
        print("Hay problemas. Copia TODO este texto y envíaselo a quien te ayuda.")
        return 1
    print("Todo bien. Arranca con:  npm run api:dev   y en otra terminal   npm run dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
