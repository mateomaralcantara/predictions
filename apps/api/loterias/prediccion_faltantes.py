import pandas as pd
from datetime import datetime

# CONFIGURACIÓN
RUTA_CSV = "resultados.csv"
LOTERIA_OBJETIVO = "lotería nacional"
RANGO_NUMEROS = range(1, 101)  # puedes ajustar esto según el rango real

# CARGA DE DATOS
df = pd.read_csv(RUTA_CSV)
df.columns = df.columns.str.strip().str.lower()
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
df = df.dropna(subset=["fecha"])
df["loteria"] = df["loteria"].str.strip().str.lower()

# FILTRAR Lotería Nacional
df_nacional = df[df["loteria"] == LOTERIA_OBJETIVO]

# COMBINAR TODOS LOS NÚMEROS APARECIDOS
todos_salidos = pd.concat([
    df_nacional["primer"],
    df_nacional["segundo"],
    df_nacional["tercero"]
])

# NUMEROS QUE NUNCA HAN SALIDO
salidos_unicos = todos_salidos.dropna().unique().tolist()
no_salidos = sorted(list(set(RANGO_NUMEROS) - set(salidos_unicos)))

print(f"🧾 Total de números posibles: {len(RANGO_NUMEROS)}")
print(f"✅ Números que han salido: {len(salidos_unicos)}")
print(f"❌ Números que NUNCA han salido: {len(no_salidos)}")
print("\n🔮 Números que podrían salir este mes (nunca antes vistos):")
print(no_salidos)

# EXTRA: Mostrar números que no han salido en los últimos 30 días
ultimo_mes = df_nacional[df_nacional["fecha"] >= datetime.now().replace(day=1)]

recientes = pd.concat([
    ultimo_mes["primer"],
    ultimo_mes["segundo"],
    ultimo_mes["tercero"]
]).dropna().unique().tolist()

potenciales_mes = sorted(list(set(RANGO_NUMEROS) - set(recientes)))

print("\n📅 Números que no han salido en lo que va del mes:")
print(potenciales_mes)
