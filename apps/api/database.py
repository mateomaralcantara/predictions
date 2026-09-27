# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de la conexión a la base de datos
DATABASE_URL = "postgresql://postgres:123456@localhost:5432/loterias_db"

# Crear motor de conexión
engine = create_engine(DATABASE_URL)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# ✅ Esta es la función que FastAPI necesita para inyectar la sesión
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
