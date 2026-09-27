

import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from main import ResultadoTradicional, Base

LOTERIAS_TRADICIONALES = [
    "Gana Más", "Lotería Nacional", "Loteria Real", "Pega 3 Más", "Quiniela Leidsa", "Florida Día", "New York Noche",
    "La Primera Día", "Primera Noche", "Quiniela Loteka", "Quiniela LoteDom", "La Suerte 12:30", "La Suerte 18:00",
    "Anguila Mañana", "Anguila Medio Día", "Anguila Tarde", "Anguila Noche", "King Lottery 12:30", "King Lottery 7:30"
]

DATABASE_URL = "postgresql://postgres:123456@localhost:5432/loterias_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def scrapear_resultados_tradicionales(fecha: date):
    fecha_str = fecha.strftime("%d-%m-%Y")
    url = f"https://loteriasdominicanas.com/?date={fecha_str}"
    print(f"🔍 Scrapeando resultados para {fecha_str}...")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("❌ Error al conectar con la página:", e)
        return

    soup = BeautifulSoup(response.text, "html.parser")
    bloques = soup.select(".game-block")

    guardados = 0

    for bloque in bloques:
        titulo = bloque.select_one(".game-title span")
        if not titulo:
            continue

        nombre_loteria = titulo.text.strip()
        if nombre_loteria not in LOTERIAS_TRADICIONALES:
            continue

        numeros = [n.text.strip() for n in bloque.select(".score")]
        if len(numeros) != 3:
            print(f"⚠️ Lotería {nombre_loteria} tiene {len(numeros)} números, se ignora.")
            continue

        existe = session.query(ResultadoTradicional).filter_by(
            fecha=fecha,
            loteria=nombre_loteria
        ).first()

        if existe:
            print(f"🔁 Ya existe {nombre_loteria} {fecha}, se omite.")
            continue

        nuevo_resultado = ResultadoTradicional(
            fecha=fecha,
            loteria=nombre_loteria,
            primer=int(numeros[0]),
            segundo=int(numeros[1]),
            tercero=int(numeros[2])
        )
        try:
            session.add(nuevo_resultado)
            session.commit()
            guardados += 1
            print(f"✅ Guardado: {nombre_loteria} - {numeros}")
        except IntegrityError:
            session.rollback()
            print(f"❌ Error al guardar {nombre_loteria}")

    if guardados == 0:
        print("⚠️ No se guardó ningún nuevo resultado.")
    else:
        print(f"🎯 {guardados} resultados guardados correctamente.")

if __name__ == "__main__":
    ultima_fecha = session.query(ResultadoTradicional.fecha).order_by(ResultadoTradicional.fecha.desc()).first()
    fecha_inicio = ultima_fecha[0] + timedelta(days=1) if ultima_fecha else date(2010, 1, 1)
    fecha_fin = date.today()

    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        scrapear_resultados_tradicionales(fecha_actual)
        fecha_actual += timedelta(days=1)