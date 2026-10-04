# buscar_numero_fechas.py

import pandas as pd

def buscar_numero(numero: int, ruta_csv: str, loteria_nombre: str = "nacional"):
    # Cargar el CSV con las fechas como datetime
    df = pd.read_csv(ruta_csv, parse_dates=["fecha"])

    # Filtrar por nombre de lotería (case-insensitive)
    df = df[df["loteria"].str.contains(loteria_nombre, case=False, na=False)]

    # Filtrar filas donde el número aparece en alguna columna
    df_filtrado = df[
        (df["primer"] == numero) |
        (df["segundo"] == numero) |
        (df["tercero"] == numero)
    ]

    # Mostrar resultados
    cantidad = len(df_filtrado)
    if cantidad == 0:
        print(f"❌ El número {numero} no ha salido en la lotería '{loteria_nombre}'.")
        return

    print(f"✅ El número {numero} ha salido {cantidad} veces en la lotería '{loteria_nombre}'.")
    print("\n📅 Fechas:")
    for _, fila in df_filtrado.iterrows():
        print(f"- {fila['fecha'].date()} → {fila['primer']}, {fila['segundo']}, {fila['tercero']}")

if __name__ == "__main__":
    numero_a_buscar = int(input("🔢 Ingresa el número que deseas buscar: "))
    buscar_numero(numero_a_buscar, "resultados_tradicionales_2010_a_hoy.csv", "nacional")
