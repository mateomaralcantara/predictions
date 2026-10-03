import pandas as pd

# Cargar el historial
df = pd.read_csv("lotto_pool_historial.csv")
df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)

# Asegúrate de que están los nombres correctos
cols = ['fecha', 'num1', 'num2', 'num3', 'num4', 'num5']
df = df.sort_values('fecha').reset_index(drop=True)

# Columna auxiliar para la secuencia ordenada
df['secuencia'] = df[['num1', 'num2', 'num3', 'num4', 'num5']].apply(lambda x: tuple(sorted(x)), axis=1)

# Marca dónde se repite una secuencia justo después de la anterior (en fechas consecutivas)
mask = (df['secuencia'] == df['secuencia'].shift(1)) & (
    (df['fecha'] - df['fecha'].shift(1)).dt.days == 1
)

# Elimina las filas donde se repite la secuencia en días seguidos
df_limpio = df[~mask].copy()

# Quitar la columna auxiliar antes de guardar
df_limpio = df_limpio[cols]
df_limpio.to_csv("lotto_pool_historial_sin_repetidos_consecutivos.csv", index=False)

print("✅ Archivo curado y guardado como 'lotto_pool_historial_sin_repetidos_consecutivos.csv'")
