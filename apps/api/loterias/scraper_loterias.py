import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

# Fecha de inicio y hoy
inicio = datetime.strptime("01-08-2010", "%d-%m-%Y")
hoy = datetime.today()

# Delay opcional para evitar bloqueo del sitio
DELAY = 1  # segundos

def scrape_dia(fecha_str):
    url = f"https://loteriasdominicanas.com/?date={fecha_str}"
    print(f"🔍 Scrapeando: {url}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        resultados = soup.find_all("div", class_="lottery-result")

        if not resultados:
            print("❌ No hay resultados para este día.")
            return

        for resultado in resultados:
            titulo = resultado.find("h3").text.strip()
            numeros = [n.text.strip() for n in resultado.find_all("span", class_="number")]
            print(f"✅ {fecha_str} - {titulo}: {numeros}")
    except Exception as e:
        print(f"🚨 Error al scrapear {fecha_str}: {e}")

# Recorrer todas las fechas
fecha_actual = inicio
while fecha_actual <= hoy:
    fecha_formateada = fecha_actual.strftime("%d-%m-%Y")
    scrape_dia(fecha_formateada)
    time.sleep(DELAY)
    fecha_actual += timedelta(days=1)
