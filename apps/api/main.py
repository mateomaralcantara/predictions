from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Date, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from collections import Counter
from datetime import datetime
from openai import OpenAI
import re
import os
from dotenv import load_dotenv
import subprocess
import csv
from pathlib import Path

# ✅ Cargar variables de entorno
load_dotenv()

# ✅ Instancia FastAPI
app = FastAPI()

# ✅ Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Conexión Base de Datos
DATABASE_URL = "postgresql://postgres:123456@localhost:5432/loterias_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

CSV_RESULTADOS = Path(__file__).resolve().parent / "loterias" / "resultados_tradicionales_2010_a_hoy.csv"

def cargar_resultados_csv():
    resultados = []
    if not CSV_RESULTADOS.exists():
        return resultados

    with CSV_RESULTADOS.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                resultados.append({
                    "fecha": row["fecha"],
                    "loteria": row["loteria"],
                    "primer": int(row["primer"]),
                    "segundo": int(row["segundo"]),
                    "tercero": int(row["tercero"]),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return resultados

def top_numeros_csv(cantidad=10, year=None, loteria=None):
    numeros = []
    for r in cargar_resultados_csv():
        if year and not str(r["fecha"]).startswith(str(year)):
            continue
        if loteria and loteria.lower() not in str(r["loteria"]).lower():
            continue
        numeros.extend([r["primer"], r["segundo"], r["tercero"]])

    return Counter(numeros).most_common(cantidad)

def ultimos_resultados_csv(cantidad=3, loteria=None):
    rows = cargar_resultados_csv()
    if loteria:
        rows = [r for r in rows if loteria.lower() in str(r["loteria"]).lower()]
    rows.sort(key=lambda r: r["fecha"], reverse=True)
    return rows[:cantidad]

# ✅ Modelo
class ResultadoTradicional(Base):
    __tablename__ = "resultados_tradicionales"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    loteria = Column(String, nullable=False)
    primer = Column(Integer)
    segundo = Column(Integer)
    tercero = Column(Integer)

# ✅ Dependency de Base de Datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Cliente OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# ✅ Funciones de análisis de datos
def buscar_top_numeros_por_año(year: str, db: Session, cantidad: int):
    try:
        fecha_inicio = f"{year}-01-01"
        fecha_fin = f"{year}-12-31"
        resultados = db.query(ResultadoTradicional).filter(ResultadoTradicional.fecha.between(fecha_inicio, fecha_fin)).all()

        numeros = []
        for r in resultados:
            numeros.extend([r.primer, r.segundo, r.tercero])
        top = Counter(numeros).most_common(cantidad)
    except Exception:
        db.rollback()
        top = top_numeros_csv(cantidad=cantidad, year=year)

    return "\n".join([f"Número {num}: {cant} veces" for num, cant in top])

def buscar_ultimos_resultados(db: Session, cantidad: int = 3, loteria: str = None):
    try:
        query = db.query(ResultadoTradicional)
        if loteria:
            query = query.filter(ResultadoTradicional.loteria.ilike(f"%{loteria}%"))
        resultados = query.order_by(ResultadoTradicional.fecha.desc()).limit(cantidad).all()
        return "\n".join([f"{r.fecha} - {r.loteria}: {r.primer}, {r.segundo}, {r.tercero}" for r in resultados])
    except Exception:
        db.rollback()
        resultados = ultimos_resultados_csv(cantidad=cantidad, loteria=loteria)
        return "\n".join([
            f'{r["fecha"]} - {r["loteria"]}: {r["primer"]}, {r["segundo"]}, {r["tercero"]}'
            for r in resultados
        ])

def numero_mas_salido_historicamente(db: Session):
    try:
        resultados = db.query(ResultadoTradicional).all()
        numeros = []
        for r in resultados:
            numeros.extend([r.primer, r.segundo, r.tercero])
        top = Counter(numeros).most_common(1)
    except Exception:
        db.rollback()
        top = top_numeros_csv(cantidad=1)

    if not top:
        return "⚠️ No hay datos históricos."

    numero, veces = top[0]
    return f"🔢 El número más salido históricamente es {numero} con {veces} apariciones."

def buscar_combinaciones_frecuentes(db: Session, cantidad: int = 5):
    try:
        resultados = db.query(ResultadoTradicional).all()
        combinaciones = [(r.primer, r.segundo, r.tercero) for r in resultados]
    except Exception:
        db.rollback()
        combinaciones = [
            (r["primer"], r["segundo"], r["tercero"])
            for r in cargar_resultados_csv()
        ]

    top = Counter(combinaciones).most_common(cantidad)
    return "\n".join([f"Combinación {comb} - {veces} veces" for comb, veces in top])

def generar_respuesta_con_openai(contexto: str, pregunta_usuario: str):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Basado exclusivamente en los siguientes datos:\n{contexto}\nResponde de forma precisa y clara al usuario."},
                {"role": "user", "content": pregunta_usuario}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error en OpenAI: {str(e)}"

def interpretar_pregunta_websocket(pregunta: str, db: Session):
    pregunta = pregunta.lower()
    match_year = re.search(r"20\d{2}", pregunta)
    year = match_year.group() if match_year else None
    match_cantidad = re.search(r"\b(\d{1,2})\b", pregunta)
    cantidad = int(match_cantidad.group()) if match_cantidad else 10

    contexto = "Datos de la base de datos:\n\n"

    palabras_top = ["top", "más salidos", "frecuentes", "salientes", "destacados", "salidores", "repetidos"]
    palabras_ultimos = ["últimos", "recientes", "más recientes", "últimas", "última vez"]
    palabras_combinaciones = ["combinaciones", "combinación", "tríos", "ternas"]
    palabras_mas_frecuente = ["número más salido", "número más frecuente", "número ganador", "más común"]

    if any(p in pregunta for p in palabras_top):
        if year:
            datos = buscar_top_numeros_por_año(year, db, cantidad)
            contexto += f"Resumen de los {cantidad} números más salidos del {year}:\n{datos}"
        else:
            datos = numero_mas_salido_historicamente(db)
            contexto += f"Resumen del número más salido históricamente:\n{datos}"

    elif any(p in pregunta for p in palabras_ultimos):
        loteria = None
        if "nacional" in pregunta:
            loteria = "nacional"
        elif "leidsa" in pregunta or "leipsa" in pregunta:
            loteria = "leidsa"
        elif "real" in pregunta:
            loteria = "real"
        datos = buscar_ultimos_resultados(db, cantidad, loteria)
        contexto += f"Resumen de los últimos {cantidad} resultados:\n{datos}"

    elif any(p in pregunta for p in palabras_combinaciones):
        datos = buscar_combinaciones_frecuentes(db, cantidad)
        contexto += f"Combinaciones más frecuentes:\n{datos}"

    elif any(p in pregunta for p in palabras_mas_frecuente):
        datos = numero_mas_salido_historicamente(db)
        contexto += f"Resumen del número más salido históricamente:\n{datos}"

    else:
        return "❌ No entendí tu pregunta. Reformúla con más claridad (por ejemplo: 'top 3 números más salidos')."

    return generar_respuesta_con_openai(contexto, pregunta)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            data = await websocket.receive_text()
            respuesta = interpretar_pregunta_websocket(data, db)
            await websocket.send_text(respuesta)
    except WebSocketDisconnect:
        print("❌ Cliente desconectado")
    finally:
        db.close()

@app.get("/api/numeros-mas-salidores")
def numeros_mas_salidores(db: Session = Depends(get_db)):
    try:
        query = """
            SELECT numero, COUNT(*) as apariciones
            FROM (
                SELECT primer as numero FROM resultados_tradicionales WHERE loteria ILIKE '%nacional%'
                UNION ALL
                SELECT segundo as numero FROM resultados_tradicionales WHERE loteria ILIKE '%nacional%'
                UNION ALL
                SELECT tercero as numero FROM resultados_tradicionales WHERE loteria ILIKE '%nacional%'
            ) AS numeros
            GROUP BY numero
            ORDER BY apariciones DESC
            LIMIT 10;
        """
        result = db.execute(text(query)).fetchall()
        return [{"numero": row[0], "apariciones": row[1]} for row in result]
    except Exception:
        db.rollback()
        top = top_numeros_csv(cantidad=10, loteria="Lotería Nacional")
        return [{"numero": numero, "apariciones": apariciones} for numero, apariciones in top]

@app.get("/api/fechas-numero")
def fechas_de_numero(numero: int = Query(...), db: Session = Depends(get_db)):
    query = text("""
        SELECT fecha, loteria
        FROM resultados_tradicionales
        WHERE primer = :num OR segundo = :num OR tercero = :num
        ORDER BY fecha
    """)
    result = db.execute(query, {"num": numero}).fetchall()
    fechas = [{"fecha": str(row.fecha), "loteria": row.loteria} for row in result]
    return {"numero": numero, "fechas": fechas}

@app.get("/")
def root():
    return {"message": "🔥 ¡LOTTERY está corriendo perfectamente! Usa WebSocket en /ws o REST en /pregunta."}

@app.get("/pregunta")
def responder_pregunta(texto: str, db: Session = Depends(get_db)):
    if not texto:
        return JSONResponse(content={"error": "❌ La pregunta no puede estar vacía"}, status_code=400)
    respuesta = interpretar_pregunta_websocket(texto, db)
    return {"pregunta": texto, "respuesta": respuesta}

@app.get("/ejecutar-scraping")
def ejecutar_scraping():
    try:
        result = subprocess.run(
            ["python", "scraper_tradicional_hasta_ayer.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return {"mensaje": "✅ Scraping ejecutado correctamente.", "salida": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"error": "❌ Falló la ejecución del scraper.", "detalle": e.stderr}
