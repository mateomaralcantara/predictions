from backend.database.connection import SessionLocal
from backend.database.models import Resultado

def limpiar_texto(texto):
    return str(texto).encode("utf-8", errors="replace").decode("utf-8")

def guardar_en_db(data: dict):
    """
    Guarda un resultado en la base de datos si no existe ya para esa fecha.
    Los 3 premios se guardan como una cadena en un solo campo: "90,34,28"
    """
    if not data:
        print("⚠️ No hay datos para guardar.")
        return

    session = SessionLocal()

    try:
        fecha = limpiar_texto(data["fecha"])
        premios = [
            limpiar_texto(data["primer_premio"]),
            limpiar_texto(data["segundo_premio"]),
            limpiar_texto(data["tercer_premio"])
        ]
        premios_str = ",".join(premios)

        existente = session.query(Resultado).filter_by(fecha=fecha).first()
        if existente:
            print(f"🔁 Ya existe resultado para {fecha}. Saltando...")
            return

        nuevo_resultado = Resultado(
            fecha=fecha,
            premios=premios_str  # 👈 nuevo campo en tu modelo
        )

        session.add(nuevo_resultado)
        session.commit()
        print(f"✅ Resultado guardado: {fecha} → {premios_str}")

    except Exception as e:
        print("❌ Error REAL al guardar en la base de datos:", repr(e))
        session.rollback()
    finally:
        session.close()
