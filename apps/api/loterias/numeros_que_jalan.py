import pandas as pd
from collections import Counter

# Ruta a tu archivo CSV
archivo_csv = "resultados.csv"

def numeros_que_jalan(numero_objetivo, archivo=archivo_csv, top=10):
    df = pd.read_csv(archivo)

    numeros_que_aparecen_con = []

    for _, fila in df.iterrows():
        numeros = [fila["primer"], fila["segundo"], fila["tercero"]]
        
        if numero_objetivo in numeros:
            # Añadir todos excepto el número objetivo
            compañeros = [n for n in numeros if n != numero_objetivo]
            numeros_que_aparecen_con.extend(compañeros)

    conteo = Counter(numeros_que_aparecen_con)
    top_resultados = conteo.most_common(top)

    print(f"\n📈 Cuando sale el número {numero_objetivo}, los que más lo acompañan son:\n")
    for i, (num, freq) in enumerate(top_resultados, start=1):
        print(f"{i:>2}. Número {int(num):02d} → {freq} veces")

# Ejecutar el análisis para el número 44 (puedes cambiarlo)
numeros_que_jalan(44)
