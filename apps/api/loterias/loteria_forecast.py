import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt

# 📁 CONFIGURACIÓN
RUTA_CSV = "resultados.csv"
LOTERIA_OBJETIVO = "lotería nacional"

# 📥 CARGA DE DATOS ROBUSTA
df = pd.read_csv(RUTA_CSV)
df.columns = df.columns.str.strip().str.lower()
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
df = df.dropna(subset=["fecha"])
df["loteria"] = df["loteria"].str.strip().str.lower()

# ✅ VERIFICAR COLUMNAS NECESARIAS
requeridas = ["fecha", "loteria", "primer", "segundo", "tercero"]
faltantes = [col for col in requeridas if col not in df.columns]
if faltantes:
    print("❌ Faltan columnas necesarias:", faltantes)
    print("Disponibles:", df.columns.tolist())
    exit()

# 🎯 FILTRAR SOLO LOTERÍA NACIONAL
df_nacional = df[df["loteria"] == LOTERIA_OBJETIVO]

if df_nacional.empty:
    print("⚠️ No hay datos de 'lotería nacional' en el archivo.")
    exit()

# 🔢 PEDIR NÚMERO
try:
    numero_input = int(input("🔢 Escribe el número que deseas analizar en Lotería Nacional: "))
except ValueError:
    print("❌ El número ingresado no es válido.")
    exit()

# 🔍 CONTAR APARICIONES
coincidencias = df_nacional[
    (df_nacional["primer"] == numero_input) |
    (df_nacional["segundo"] == numero_input) |
    (df_nacional["tercero"] == numero_input)
]

conteo = len(coincidencias)

print(f"\n🔍 El número {numero_input} ha salido {conteo} veces en 'lotería nacional'.")

if conteo == 0:
    print("⚠️ No hay datos suficientes para hacer predicción.")
    exit()

# 👀 Mostrar primeras fechas donde apareció
print("\n🗓️ Primeras apariciones:")
print(coincidencias[["fecha", "primer", "segundo", "tercero"]].head(10))

# 📊 AGRUPAR Y ENTRENAR
conteo_diario = coincidencias.groupby("fecha").size().reset_index(name="apariciones")
conteo_diario.rename(columns={"fecha": "ds", "apariciones": "y"}, inplace=True)

modelo = Prophet()
modelo.fit(conteo_diario)

# 🔮 PREDECIR
futuro = modelo.make_future_dataframe(periods=30)
forecast = modelo.predict(futuro)

# 📈 GRAFICAR
fig = modelo.plot(forecast)
plt.title(f"📈 Predicción para el número {numero_input} en Lotería Nacional")
plt.xlabel("Fecha")
plt.ylabel("Frecuencia estimada")
plt.tight_layout()
plt.show()
