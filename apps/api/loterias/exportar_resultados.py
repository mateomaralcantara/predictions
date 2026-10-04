from sqlalchemy import create_engine
import pandas as pd

# Conexión a la base de datos
engine = create_engine('postgresql://postgres:123456@localhost:5432/loterias_db')

# Ejecutar la consulta y guardar en DataFrame
query = "SELECT * FROM resultados_tradicionales WHERE fecha >= '2010-08-01' ORDER BY fecha"
df = pd.read_sql_query(query, engine)

# Exportar a CSV
df.to_csv("resultados_tradicionales_2010_a_hoy.csv", index=False, encoding="utf-8")

print("✅ Exportado exitosamente a resultados_tradicionales_2010_a_hoy.csv")
