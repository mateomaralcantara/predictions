# actualizar_resultados.py

import pandas as pd
from datetime import datetime, timedelta

# 1. Cargar archivo existente (si existe)
try:
    df_viejo = pd.read_csv('resultados.csv')
    ultima_fecha = pd.to_datetime(df_viejo['fecha']).max()
except FileNotFoundError:
    df_viejo = pd.DataFrame(columns=['fecha', 'loteria', 'numeros'])
    ultima_fecha = datetime(2010, 1, 1) # Cambia si tu historial es más reciente

# 2. SCRAPING desde la última fecha + 1 hasta hoy
from scraper_tradicional_hasta_ayer import scrape_day # Debe existir esta función

hoy = datetime.now().date()
fechas = pd.date_range(ultima_fecha + timedelta(days=1), hoy)

# Acumular resultados nuevos
nuevos = []
for fecha in fechas:
    dia = fecha.strftime('%d-%m-%Y')
    print(f"🔍 Scrapeando {dia}...")
    resultados = scrape_day(dia)  # Debes adaptar tu scraper para que retorne una lista de dicts: [{'fecha':..., 'loteria':..., 'numeros':...}]
    nuevos.extend(resultados)

df_nuevos = pd.DataFrame(nuevos)
# Si no hay nuevos, no hacemos nada
if not df_nuevos.empty:
    df_full = pd.concat([df_viejo, df_nuevos]).drop_duplicates(subset=['fecha', 'loteria', 'numeros'])
    df_full.to_csv('resultados.csv', index=False)
    print("✅ ¡CSV actualizado hasta hoy!")
else:
    print("No hay resultados nuevos para añadir.")

