import psycopg2
from collections import Counter
import itertools

# Conexión
conn = psycopg2.connect(
    dbname="loteria",
    user="postgres",
    password="123456",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

cur.execute("SELECT numeros FROM leidsa_loto")
registros = cur.fetchall()
conn.close()

# Contar frecuencia de cada número
contador = Counter()
for fila in registros:
    for n in fila[0]:
        contador[n] += 1

top_15 = [num for num, _ in contador.most_common(15)]

# Predecir combinaciones posibles
combinaciones = list(itertools.combinations(top_15, 6))
combinaciones_ordenadas = sorted(combinaciones, key=lambda comb: sum(contador[n] for n in comb), reverse=True)

print("🔮 Top 10 combinaciones más probables:")
for comb in combinaciones_ordenadas[:10]:
    print(comb)
