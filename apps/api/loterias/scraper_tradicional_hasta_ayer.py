import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date

# Nombre del CSV y loterías tradicionales
CSV_FILE = "resultados_tradicionales_2010_a_hoy.csv"
LOTERIAS_TRADICIONALES = [
    "Gana Más", "Lotería Nacional", "Loteria Real", "Pega 3 Más", "Quiniela Leidsa", "Florida Día", "New York Noche",
    "La Primera Día", "Primera Noche", "Quiniela Loteka", "Quiniela LoteDom", "La Suerte 12:30", "La Suerte 18:00",
    "Anguila Mañana", "Anguila Medio Día", "Anguila Tarde", "Anguila Noche", "King Lottery 12:30", "King Lottery 7:30"
]

# Carga CSV existente (si no existe, crea DataFrame vacío)
try:
    df = pd.read_csv(CSV_FILE, parse_dates=['fecha'])
    print(f"Archivo encontrado. Última fecha: {df['fecha'].max().date()}")
except FileNotFoundError:
    print("No existe el archivo, se creará uno nuevo.")
    df = pd.DataFrame(columns=['fecha', 'loteria', 'primer', 'segundo', 'tercero'])

# Definir el rango de fechas a scrapear
ultima_fecha = df['fecha'].max() if not df.empty else pd.Timestamp("2010-01-01")
fecha_inicio = (ultima_fecha + pd.Timedelta(days=1)).date()
fecha_fin = (date.today() - timedelta(days=1))

# Función para scrapear un día
def scrapear_resultados_tradicionales(fecha: date):
    fecha_str = fecha.strftime("%d-%m-%Y")
    url = f"https://loteriasdominicanas.com/?date={fecha_str}"
    print(f"Scrapeando resultados para {fecha_str}...")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Error al conectar con la página:", e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    bloques = soup.select(".game-block")

    resultados = []
    for bloque in bloques:
        titulo = bloque.select_one(".game-title span")
        if not titulo:
            continue
        nombre_loteria = titulo.text.strip()
        if nombre_loteria not in LOTERIAS_TRADICIONALES:
            continue
        numeros = [n.text.strip() for n in bloque.select(".score")]
        if len(numeros) != 3:
            continue
        resultados.append({
            "fecha": fecha,
            "loteria": nombre_loteria,
            "primer": int(numeros[0]),
            "segundo": int(numeros[1]),
            "tercero": int(numeros[2])
        })
    return resultados

# Bucle de scrap
nuevos = []
fecha_actual = fecha_inicio
while fecha_actual <= fecha_fin:
    res = scrapear_resultados_tradicionales(fecha_actual)
    nuevos.extend(res)
    fecha_actual += timedelta(days=1)

# Guardar solo si hay nuevos resultados
if nuevos:
    nuevos_df = pd.DataFrame(nuevos)
    df = pd.concat([df, nuevos_df], ignore_index=True)
    df = df.drop_duplicates(subset=['fecha', 'loteria'])
    df = df.sort_values(by=['fecha', 'loteria'])
    df.to_csv(CSV_FILE, index=False, date_format='%Y-%m-%d')
    print(f"{len(nuevos)} resultados nuevos agregados.")
else:
    print("No hay resultados nuevos para agregar.")
