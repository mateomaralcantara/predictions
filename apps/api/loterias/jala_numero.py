import pandas as pd
from collections import Counter

def numeros_que_jalan(numero_objetivo, archivo="resultados.csv", top=10):
    df = pd.read_csv(archivo)
    numero_objetivo = int(numero_objetivo)
    
    acompañantes = []

    for _, fila in df.iterrows():
        numeros = [fila["primer"], fila["segundo"], fila["tercero"]]
        if numero_objetivo in numeros:
            otros = [n for n in numeros if n != numero_objetivo]
            acompañantes.extend(otros)

    conteo = Counter(acompañantes)
    resultados = conteo.most_common(top)

    print(f"\n🔍 Cuando sale el número {numero_objetivo}, los que más lo acompañan son:\n")
    for i, (n, veces) in enumerate(resultados, 1):
        print(f"{i:>2}. Número {int(n):02d} → {veces} veces")

if __name__ == "__main__":
    print("🎯 Analizador de Números Jaladores")
    numero = input("👉 Escribe un número (00 al 99): ")
    numeros_que_jalan(numero)
