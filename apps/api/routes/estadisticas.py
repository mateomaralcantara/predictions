from fastapi import APIRouter
from sqlalchemy import create_engine
import pandas as pd

router = APIRouter()

@router.get("/numeros-top-nacional")
def numeros_top_nacional():
    engine = create_engine('postgresql://postgres:123456@localhost:5432/loterias_db')
    query = """
    SELECT numero, COUNT(*) as apariciones
    FROM resultados_tradicionales
    WHERE loteria = 'Lotería Nacional'
    GROUP BY numero
    ORDER BY apariciones DESC
    LIMIT 3;
    """
    df = pd.read_sql_query(query, engine)
    return df.to_dict(orient="records")
