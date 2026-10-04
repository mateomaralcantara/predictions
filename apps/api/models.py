# backend/models.py
from sqlalchemy import Column, Integer, String, Date
from .database import Base

# ✅ Modelo para resultados tradicionales (3 números)
class ResultadoTradicional(Base):
    __tablename__ = "resultados_tradicionales"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    loteria = Column(String, nullable=False)
    primer = Column(Integer)
    segundo = Column(Integer)
    tercero = Column(Integer)

# ✅ Modelo para resultados de loterías tipo Loto (6-7 números)
class ResultadoLoto(Base):
    __tablename__ = "resultados_loto"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    loteria = Column(String, nullable=False)
    num1 = Column(Integer)
    num2 = Column(Integer)
    num3 = Column(Integer)
    num4 = Column(Integer)
    num5 = Column(Integer)
    num6 = Column(Integer)
    num7 = Column(Integer)
