"""Comandos de administración.

python -m app.cli migrar
python -m app.cli importar-csv [ruta.csv]
python -m app.cli crear-admin correo@dominio.com
python -m app.cli dar-plan correo@dominio.com platinum --dias 30
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from . import auth
from .config import get_settings
from .db import ResultadoTradicional, Suscripcion, Usuario, session_factory, utcnow
from .migrate import upgrade
from .payments import PLANES
from .repository import load_csv


def _ocultar(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    esquema, resto = url.split("://", 1)
    cred, host = resto.rsplit("@", 1)
    return f"{esquema}://{cred.split(':', 1)[0]}:***@{host}"


def importar_csv(ruta: Path, url: str) -> tuple[int, int]:
    """Inserta en la base los sorteos del CSV que no estén ya (por fecha+lotería)."""
    filas = load_csv(ruta)
    Session = session_factory(url)
    with Session() as db:
        existentes = set(db.execute(select(ResultadoTradicional.fecha, ResultadoTradicional.loteria)).all())
        nuevos, vistos = [], set()
        for r in filas:
            clave = (r.fecha, r.loteria)
            if clave in existentes or clave in vistos:
                continue
            vistos.add(clave)
            nuevos.append(
                ResultadoTradicional(
                    fecha=r.fecha, loteria=r.loteria, primer=r.primer, segundo=r.segundo, tercero=r.tercero
                )
            )
        for i in range(0, len(nuevos), 2000):
            db.add_all(nuevos[i : i + 2000])
            db.flush()
        db.commit()
    return len(nuevos), len(filas) - len(nuevos)


def crear_admin(email: str, password: str, nombre: str, url: str) -> Usuario:
    email = auth.normalizar_email(email)
    if not auth.email_valido(email):
        raise SystemExit("Correo inválido.")
    if len(password) < 12:
        raise SystemExit("La contraseña de administrador debe tener al menos 12 caracteres.")
    Session = session_factory(url)
    with Session() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None:
            usuario = Usuario(email=email, nombre=nombre, password_hash="")
            db.add(usuario)
        usuario.password_hash = auth.hash_password(password)
        usuario.es_admin = True
        db.commit()
        return usuario


def dar_plan(email: str, plan: str, dias: int, url: str) -> Suscripcion:
    if plan not in PLANES:
        raise SystemExit(f"Plan desconocido. Opciones: {', '.join(PLANES)}")
    Session = session_factory(url)
    with Session() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == auth.normalizar_email(email)))
        if usuario is None:
            raise SystemExit("No existe un usuario con ese correo.")
        ahora = utcnow()
        sus = Suscripcion(usuario_id=usuario.id, plan=plan, inicio=ahora, fin=ahora + timedelta(days=dias))
        db.add(sus)
        db.commit()
        return sus


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    ap = argparse.ArgumentParser(prog="python -m app.cli", description="Administración de Predictions RD")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrar", help="Aplica las migraciones pendientes")
    p_imp = sub.add_parser("importar-csv", help="Importa resultados tradicionales a la base de datos")
    p_imp.add_argument("ruta", nargs="?", type=Path, default=settings.resultados_csv)
    p_adm = sub.add_parser("crear-admin", help="Crea o promueve un administrador")
    p_adm.add_argument("email")
    p_adm.add_argument("--nombre", default="Administrador")
    p_plan = sub.add_parser("dar-plan", help="Regala un plan a un usuario (soporte, cortesía)")
    p_plan.add_argument("email")
    p_plan.add_argument("plan", choices=list(PLANES))
    p_plan.add_argument("--dias", type=int, default=30)
    args = ap.parse_args(argv)

    url = settings.app_database_url
    if args.cmd == "migrar":
        upgrade(url)
        print("Migraciones aplicadas.")
    elif args.cmd == "importar-csv":
        destino = settings.database_url or url
        print(f"Destino: {_ocultar(destino)}")
        if destino.startswith("sqlite"):
            print(
                "AVISO: no hay DATABASE_URL ni SUPABASE_DB_URL; se importa al SQLite LOCAL.\n"
                "       Para subirlo a Supabase añade SUPABASE_DB_URL en .env.local (npm run setup)."
            )
        upgrade(destino)
        nuevos, omitidos = importar_csv(args.ruta, destino)
        print(f"Importados {nuevos} sorteos ({omitidos} ya existían o estaban repetidos).")
    elif args.cmd == "crear-admin":
        upgrade(url)
        pw = getpass.getpass("Contraseña (mín. 12): ")
        if pw != getpass.getpass("Repite la contraseña: "):
            raise SystemExit("Las contraseñas no coinciden.")
        u = crear_admin(args.email, pw, args.nombre, url)
        print(f"Administrador listo: {u.email}")
    elif args.cmd == "dar-plan":
        upgrade(url)
        s = dar_plan(args.email, args.plan, args.dias, url)
        print(f"Plan {s.plan} activo hasta {s.fin:%Y-%m-%d}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
