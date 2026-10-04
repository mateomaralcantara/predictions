import pandas as pd

# 📁 CONFIGURACIÓN
RUTA_CSV = "resultados.csv"
LOTERIA_OBJETIVO = "lotería nacional"

# 📥 CARGA ROBUSTA
df = pd.read_csv(RUTA_CSV)
df.columns = df.columns.str.strip().str.lower()
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
df = df.dropna(subset=["fecha"])
df["loteria"] = df["loteria"].str.strip().str.lower()

# 🎯 FILTRAR SÓLO LOTERÍA NACIONAL
df_nacional = df[df["loteria"] == LOTERIA_OBJETIVO]

if df_nacional.empty:
    print("⚠️ No hay datos de 'lotería nacional' en el archivo.")
    exit()

# 🧠 FUNCIÓN PARA CONTAR FRECUENCIAS
def top_numeros(columna, top=10):
    return df_nacional[columna].value_counts().head(top)

# 📊 TOP 10 POR POSICIÓN
print("\n🔢 Top 10 - Primer lugar:")
print(top_numeros("primer"))

print("\n🔢 Top 10 - Segundo lugar:")
print(top_numeros("segundo"))

print("\n🔢 Top 10 - Tercer lugar:")
print(top_numeros("tercero"))

# 📈 Top combinados
print("\n📊 Top 10 números más frecuentes en cualquier posición:")
todos = pd.concat([
    df_nacional["primer"],
    df_nacional["segundo"],
    df_nacional["tercero"]
])
print(todos.value_counts().head(10))
