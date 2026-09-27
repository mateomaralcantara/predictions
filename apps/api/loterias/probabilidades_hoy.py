# probabilidades_hoy.py

import pandas as pd
from collections import Counter
from datetime import datetime

def calcular_probabilidades(ruta_csv: str, loteria_nombre: str = "nacional"):
    # Carga de datos
    df = pd.read_csv(ruta_csv, parse_dates=["fecha"])

    # Filtrar solo la lotería nacional (nombre que contiene "nacional", case‑insensitive)
    df = df[df["loteria"].str.contains(loteria_nombre, case=False, na=False)]

    # Fecha de hoy (solo día y mes)
    hoy = datetime.now()
    dia = hoy.day
    mes = hoy.month

    # Filtramos todos los resultados con el mismo día y mes (cualquier año)
    df_hoy = df[(df["fecha"].dt.day == dia) & (df["fecha"].dt.month == mes)]

    # Contamos apariciones de cada número en today
    numeros = df_hoy[["primer", "segundo", "tercero"]].values.flatten()
    conteo = Counter(numeros)

    # Resultados
    total_eventos = len(df_hoy)
    if total_eventos == 0:
        print(f"No hay datos históricos para la Lotería Nacional en {dia:02d}-{mes:02d}")
        return

    print(f"Histórico para Lotería Nacional en fecha {dia:02d}-{mes:02d} a través de {total_eventos} sorteos:\n")
    for num, freq in conteo.most_common(10):
        prob = freq / total_eventos * 100
        print(f"Número {num}: salió {freq} veces → probabilidad ≈ {prob:.2f}%")

if __name__ == "__main__":
    ruta_csv = "resultados.csv"
    calcular_probabilidades(ruta_csv)
