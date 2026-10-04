import pandas as pd
from collections import Counter
from itertools import combinations

# Cambia por la ruta correcta si no está en la misma carpeta
archivo_csv = "resultados.csv"

def obtener_palets_mas_salidores(archivo, top=20):
    df = pd.read_csv(archivo)

    # Asegúrate de que las columnas existan y se llamen así
    palets = []

    for _, row in df.iterrows():
        numeros = [row["primer"], row["segundo"], row["tercero"]]
        
        # Validamos que todos sean enteros válidos
        if all(pd.notnull(n) and isinstance(n, (int, float)) for n in numeros):
            numeros = [int(n) for n in numeros]
            # Combinaciones de 2 sin importar el orden
            pares = combinations(numeros, 2)
            for par in pares:
                palet = tuple(sorted(par))
                palets.append(palet)

    # Contamos frecuencia de cada palé
    conteo = Counter(palets)
    top_palets = conteo.most_common(top)

    print("🔝 Top {} Palés más salidores:".format(top))
    for i, (palet, veces) in enumerate(top_palets, start=1):
        print(f"{i:>2}. Palé {palet[0]:02d}-{palet[1]:02d} → {veces} veces")

# Ejecutar
obtener_palets_mas_salidores(archivo_csv)
