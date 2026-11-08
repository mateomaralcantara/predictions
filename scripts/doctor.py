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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks import (  # noqa: E402
    ocultar_url,
    probar_db,
    probar_gemini,
    probar_supabase,
    tipo_clave_supabase,
    variables_vite_peligrosas,
)

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

    archivos = [ROOT / ".env.local", API / ".env.local", API / ".env", ROOT / ".env"]
    hay = [f for f in archivos if f.exists()]
    check(bool(hay), "", "No hay .env.local: ejecuta  npm run setup  para crearlo", grave=False)
    for i, env_file in enumerate(hay):
        nombres = [
            line.split("=", 1)[0].strip()
            for line in env_file.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            if "=" in line and not line.strip().startswith("#") and line.split("=", 1)[1].strip()
        ]
        rol = "principal" if i == 0 else "secundario (lo que ya defina el principal se ignora)"
        print(f"{AVISO if i else OK} {env_file.relative_to(ROOT)} [{rol}]: {', '.join(nombres) or '(vacío)'}")

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
        print(f"       Base de datos de la app: {ocultar_url(s.app_database_url)}")
        if s.gemini_api_key:
            ok, msg = probar_gemini(s.gemini_api_key, s.gemini_model)
            check(ok, f"Gemini: {msg}", f"Gemini: {msg}")
        revisar_supabase()
        if s.database_url:
            ok, msg = probar_db(s.database_url)
            check(ok, f"Base de datos: {msg}", f"No conecta con {ocultar_url(s.database_url)}: {msg}", grave=False)
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


def revisar_supabase() -> None:
    url = os.environ.get("SUPABASE_URL", "").strip()
    pub = (os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "").strip()
    sec = (os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    peligrosas = variables_vite_peligrosas({k: v for k, v in os.environ.items()})
    check(
        not peligrosas,
        "Ningún secreto expuesto al navegador (VITE_*)",
        f"Estas variables VITE_ parecen secretas y llegarían al navegador: {', '.join(peligrosas)}",
    )
    if not (url or pub or sec):
        print(f"{AVISO} Supabase: SUPABASE_URL y claves no definidas (opcional)")
        return
    check(bool(url), f"SUPABASE_URL: {url}", "Falta SUPABASE_URL (https://<proyecto>.supabase.co)")
    for nombre, valor, esperado in (
        ("publishable/anon", pub, ("publishable", "legacy")),
        ("secret/service_role", sec, ("secret", "legacy")),
    ):
        if not valor:
            print(f"{AVISO} Supabase: clave {nombre} no definida")
            continue
        tipo = tipo_clave_supabase(valor)
        if not check(
            tipo in esperado,
            f"Clave {nombre}: formato correcto ({tipo}, …{valor[-4:]})",
            f"La clave {nombre} tiene formato «{tipo}»: ¿la pegaste en la variable equivocada?",
        ):
            continue
        if url:
            ok, msg = probar_supabase(url, valor)
            check(ok, f"Clave {nombre}: {msg}", f"Clave {nombre}: {msg}")


def resumen() -> int:
    print()
    if problemas:
        print("Hay problemas. Copia TODO este texto y envíaselo a quien te ayuda.")
        return 1
    print("Todo bien. Arranca con:  npm run api:dev   y en otra terminal   npm run dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
