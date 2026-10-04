from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Resultado

router = APIRouter()

# Dependencia para obtener la sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ruta GET para consultar todos los resultados
@router.get("/resultados", response_model=list[dict])
def get_resultados(db: Session = Depends(get_db)):
    resultados = db.query(Resultado).all()
    return [r.__dict__ for r in resultados if "_sa_instance_state" not in r.__dict__]
