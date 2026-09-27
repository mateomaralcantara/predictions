import pandas as pd

# Cargar el CSV
df = pd.read_csv("resultados.csv")

# Normalizar columnas
df.columns = df.columns.str.strip().str.lower()

# Filtrar solo la lotería nacional
df_nacional = df[df["loteria"].str.strip().str.lower() == "lotería nacional"]

# Mostrar 10 fechas crudas sin convertir
print("\n📅 Fechas RAW (sin procesar):")
print(df_nacional["fecha"].head(10))

# Mostrar combinación fecha + primer + segundo + tercero
print("\n🧪 Primeras 10 filas con datos:")
print(df_nacional[["fecha", "primer", "segundo", "tercero"]].head(10))

# Forzar conversión y ver errores
df_nacional["fecha_parseada"] = pd.to_datetime(df_nacional["fecha"], errors="coerce")
print("\n🔍 Fechas después de intentar convertir con errors='coerce':")
print(df_nacional[["fecha", "fecha_parseada"]].head(10))
