import pandas as pd

df = pd.read_csv("resultados.csv")
df.columns = df.columns.str.strip().str.lower()
df['loteria'] = df['loteria'].str.lower().str.strip()

# Solo lotería nacional
df_nacional = df[df['loteria'] == "loteria nacional"]

# Verifica tipos y valores únicos
print("🔎 Tipos de datos:")
print(df_nacional[['primer', 'segundo', 'tercero']].dtypes)

print("\n🧮 Valores únicos (primer número):")
print(df_nacional['primer'].unique())

print("\n🎰 Loterías disponibles:")
print(df['loteria'].unique())

print("\n📊 Cantidad de filas por lotería:")
print(df['loteria'].value_counts())

df_nacional = df[df['loteria'] == "loteria nacional"]
print("\n📅 Fechas disponibles en 'loteria nacional':")
print(df_nacional['fecha'].unique())

print("\n📄 Primeras 5 filas:")
print(df_nacional.head())

