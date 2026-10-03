import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import os

BASE_URL = "https://loteriasdominicanas.com/?date={date}"
ARCHIVO_CSV = "resultados.csv"

# Esta función guarda cada resultado en el CSV
def guardar_resultado(fecha, premios, fuente, loteria, tipo_sorteo):
    archivo_existe = os.path.isfile(ARCHIVO_CSV)
    with open(ARCHIVO_CSV, mode='a', newline='', encoding='utf-8') as archivo:
        writer = csv.writer(archivo)
        if not archivo_existe:
            writer.writerow(["fecha", "premios", "fuente", "loteria", "tipo_sorteo"])  # encabezados
        writer.writerow([fecha, premios, fuente, loteria, tipo_sorteo])

# Esta función scrapea una sola fecha
def obtener_resultado(fecha_str):
    url = BASE_URL.format(date=fecha_str)
    print(f"🔍 Scrapeando {fecha_str}... {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        bloques = soup.select(".game-block")

        if not bloques:
            print(f"⚠️ No se encontraron bloques para {fecha_str}")
            return

        for bloque in bloques:
            try:
                titulo_el = bloque.select_one(".game-title span")
                if not titulo_el:
                    continue
                titulo = titulo_el.text.strip()

                if "Gana Más" not in titulo and "Lotería Nacional" not in titulo:
                    continue  # solo esas dos

                numeros_el = bloque.select(".game-scores .score")
                if len(numeros_el) < 3:
                    print(f"⛔ Sorteo incompleto ({titulo}) en {fecha_str}")
                    continue

                numeros = [n.text.strip() for n in numeros_el[:3]]
                premios = ",".join(numeros)

                guardar_resultado(
                    fecha=fecha_str,
                    premios=premios,
                    fuente=url,
                    loteria=titulo,
                    tipo_sorteo="desconocido"
                )

                print(f"✅ {titulo} -> {premios}")
            except Exception as e:
                print(f"❌ Error en bloque: {e}")

    except Exception as e:
        print(f"❌ Error al scrapear {fecha_str}: {e}")

# Scrapea un rango completo
def scrapear_rango(fecha_inicio, fecha_final):
    actual = fecha_inicio
    while actual <= fecha_final:
        fecha_str = actual.strftime("%d-%m-%Y")
        obtener_resultado(fecha_str)
        actual += timedelta(days=1)

if __name__ == "__main__":
    inicio = datetime(2010, 8, 1)
    fin = datetime(2025, 3, 31)
    scrapear_rango(inicio, fin)
