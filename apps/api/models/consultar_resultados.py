from sqlalchemy import create_engine

engine = create_engine('postgresql://dayka:123456@localhost:5432/loterias_db')

with engine.connect() as conn:
    result = conn.execute("SELECT * FROM resultados_tradicionales WHERE fecha >= '2010-08-01' ORDER BY fecha")
    for row in result:
        print(row)
