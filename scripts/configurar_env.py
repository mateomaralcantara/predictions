"""Asistente para crear/actualizar .env.local:   npm run setup

- Parte de .env.example y conserva sus comentarios.
- Las claves se escriben sin mostrarse en pantalla.
- Enter = mantener el valor actual · "-" = borrarlo.
- Genera SECRET_KEY y ADMIN_TOKEN si faltan.
- Al final prueba de verdad Gemini y la base de datos.
"""

from __future__ import annotations

import getpass
import re
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks import ocultar_url, probar_db, probar_gemini  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLANTILLA = ROOT / ".env.example"
DESTINO = ROOT / ".env.local"
LEGADO = ROOT / "apps" / "api" / ".env"
LINEA = re.compile(r"^(#\s*)?([A-Z][A-Z0-9_]*)=(.*)$")

PREGUNTAS = [
    # (variable, texto, secreta)
    ("GEMINI_API_KEY", "Clave de Gemini (https://aistudio.google.com/app/apikey)", True),
    ("SUPABASE_DB_URL", "Connection string de Supabase (Settings → Database → URI)", True),
    ("PAYPAL_CLIENT_ID", "PayPal Client ID", False),
    ("PAYPAL_SECRET", "PayPal Secret", True),
]


def leer(path: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if path.exists():
        for linea in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = LINEA.match(linea.strip())
            if m and not m.group(1) and m.group(3).strip():
                valores[m.group(2)] = m.group(3).strip().strip('"').strip("'")
    return valores


def escribir(valores: dict[str, str]) -> None:
    salida, usadas = [], set()
    for linea in PLANTILLA.read_text(encoding="utf-8").splitlines():
        m = LINEA.match(linea.strip())
        if m and m.group(2) in valores:
            clave = m.group(2)
            if clave in usadas:
                continue
            usadas.add(clave)
            salida.append(f"{clave}={valores[clave]}")
        else:
            salida.append(linea)
    extra = [k for k in valores if k not in usadas]
    if extra:
        salida += ["", "# ── Otras variables ─────────────────────────────────────────────────"]
        salida += [f"{k}={valores[k]}" for k in extra]
    DESTINO.write_text("\n".join(salida) + "\n", encoding="utf-8")


def resumen_valor(clave: str, valor: str | None) -> str:
    if not valor:
        return "vacío"
    if clave.endswith("_URL") and "@" in valor:
        return ocultar_url(valor)
    if clave.endswith(("_KEY", "SECRET", "TOKEN")):
        return f"configurada (…{valor[-4:]})"
    return valor


def preguntar(texto: str, actual: str | None, secreta: bool) -> str | None:
    sufijo = f" [{resumen_valor('X_KEY' if secreta else 'X', actual)}]"
    pedir = getpass.getpass if secreta else input
    r = pedir(f"  {texto}{sufijo}: ").strip()
    if r == "":
        return actual
    if r == "-":
        return None
    return r


def main() -> int:
    print(f"Configurando {DESTINO.name} (Enter = mantener · '-' = borrar)\n")
    valores = leer(DESTINO)
    if not valores and LEGADO.exists():
        heredados = leer(LEGADO)
        if heredados and input(f"  Importar {len(heredados)} valores de apps/api/.env? [S/n]: ").strip().lower() in (
            "",
            "s",
            "si",
            "sí",
            "y",
        ):
            valores.update(heredados)

    for clave, texto, secreta in PREGUNTAS:
        nuevo = preguntar(texto, valores.get(clave), secreta)
        if nuevo:
            valores[clave] = nuevo
        else:
            valores.pop(clave, None)

    if valores.get("PAYPAL_CLIENT_ID"):
        modo = input("  PayPal en modo (s)andbox o (r)eal? [s]: ").strip().lower()
        valores["PAYPAL_BASE_URL"] = (
            "https://api-m.paypal.com" if modo.startswith("r") else "https://api-m.sandbox.paypal.com"
        )

    for clave in ("SECRET_KEY", "ADMIN_TOKEN"):
        if not valores.get(clave):
            valores[clave] = secrets.token_urlsafe(48)
            print(f"  {clave} generada automáticamente.")
    valores.setdefault("ENVIRONMENT", "development")
    valores.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

    escribir(valores)
    print(f"\nGuardado en {DESTINO} (no se sube a Git).\n\nComprobando…")
    if valores.get("GEMINI_API_KEY"):
        ok, msg = probar_gemini(valores["GEMINI_API_KEY"], valores["GEMINI_MODEL"])
        print(f"  {'[OK]   ' if ok else '[FALLA]'} Gemini: {msg}")
    url = valores.get("DATABASE_URL") or valores.get("SUPABASE_DB_URL")
    if url:
        ok, msg = probar_db(url)
        print(f"  {'[OK]   ' if ok else '[FALLA]'} Base de datos {ocultar_url(url)}: {msg}")
        if ok:
            print("         Para subir el histórico a esa base:  npm run cli -- importar-csv")
    print("\nListo. Revisa todo con:  npm run doctor")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado; no se guardó nada nuevo.")
        sys.exit(1)
