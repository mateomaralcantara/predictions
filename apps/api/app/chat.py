"""Asistente de preguntas sobre el histórico.

1. Se interpreta la pregunta con reglas deterministas y se calcula la
   respuesta con los datos reales (funciona sin OpenAI).
2. Si hay ``OPENAI_API_KEY``, el modelo solo redacta la respuesta en lenguaje
   natural a partir de esos datos. Si falla, se devuelve la respuesta local.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date

from . import stats
from .config import Settings
from .repository import Resultado

log = logging.getLogger(__name__)

MAX_PREGUNTA = 500

# alias -> fragmento (normalizado) del nombre de la lotería en los datos
ALIAS_LOTERIAS: dict[str, str] = {
    "nacional": "loteria nacional",
    "leidsa": "quiniela leidsa",
    "leipsa": "quiniela leidsa",
    "loteka": "loteka",
    "lotedom": "lotedom",
    "gana mas": "gana mas",
    "pega 3": "pega 3",
    "new york": "new york",
    "nueva york": "new york",
    "florida": "florida",
    "anguila": "anguila",
    "king": "king lottery",
    "la suerte": "la suerte",
    "la primera": "primera",
}

AYUDA = (
    "Puedo responder sobre el histórico de loterías tradicionales. Prueba con:\n"
    "• «top 10 números más salidos de 2024 en la Nacional»\n"
    "• «últimos 5 resultados de Leidsa»\n"
    "• «¿cuándo salió el 23?»\n"
    "• «números más atrasados de Loteka»\n"
    "• «combinaciones más repetidas»"
)

DISCLAIMER = "Recuerda: los sorteos son aleatorios; el histórico no aumenta la probabilidad de ganar."


@dataclass
class Consulta:
    intencion: str
    loteria: str | None = None
    year: int | None = None
    cantidad: int = 10
    numero: int | None = None


@dataclass
class Respuesta:
    intencion: str
    texto: str
    datos: object = None


def _palabras(texto: str, *opciones: str) -> bool:
    return any(o in texto for o in opciones)


def interpretar(pregunta: str) -> Consulta:
    q = stats.normalizar(pregunta)[:MAX_PREGUNTA]

    year_match = re.search(r"\b(20[0-4]\d)\b", q)
    year = int(year_match.group(1)) if year_match else None

    loteria = None
    for alias, fragmento in ALIAS_LOTERIAS.items():
        if alias in q:
            loteria = fragmento
            break

    cantidad = 10
    m = re.search(r"\b(?:top|primeros|ultimos|ultimas)\s+(\d{1,3})\b", q) or re.search(
        r"\b(\d{1,3})\s+(?:numeros|resultados|sorteos|combinaciones|ternas|atrasados)\b", q
    )
    if m:
        cantidad = max(1, min(50, int(m.group(1))))

    q_sin_year = re.sub(r"\b20[0-4]\d\b", " ", q)
    num_match = re.search(r"(?:numero|el|del|al)\s+(\d{1,2})\b(?!\s+(?:numeros|resultados|sorteos))", q_sin_year)

    if _palabras(q, "ayuda", "que puedes", "como funciona", "hola"):
        intencion = "ayuda"
    elif _palabras(q, "atrasad", "no sale", "no han salido", "frio", "frios"):
        intencion = "atrasados"
    elif _palabras(q, "combinacion", "terna", "trio"):
        intencion = "combinaciones"
    elif _palabras(q, "ultimo", "ultima", "reciente", "resultado de hoy", "salio hoy", "ayer"):
        intencion = "ultimos"
    elif num_match and _palabras(q, "cuando", "veces", "fechas", "salio", "ha salido", "numero"):
        intencion = "numero"
    elif _palabras(q, "top", "mas salid", "frecuente", "salidor", "repetido", "caliente", "mas comun", "ganador"):
        intencion = "top"
    else:
        intencion = "desconocida"

    numero = int(num_match.group(1)) if (intencion == "numero" and num_match) else None
    if intencion == "top" and not m and _palabras(q, "el numero mas", "numero mas"):
        cantidad = 1
    return Consulta(intencion, loteria, year, cantidad, numero)


def _ambito(c: Consulta) -> str:
    partes = []
    if c.loteria:
        partes.append(f"en «{c.loteria}»")
    if c.year:
        partes.append(f"en {c.year}")
    return (" " + " ".join(partes)) if partes else " (todas las loterías)"


def _fmt(n: int) -> str:
    return f"{n:02d}"


def responder_local(consulta: Consulta, rows: list[Resultado]) -> Respuesta:
    c = consulta
    if c.intencion == "ayuda":
        return Respuesta("ayuda", AYUDA)
    if c.intencion == "desconocida":
        return Respuesta("desconocida", "No entendí la pregunta. " + AYUDA)

    datos = stats.filtrar(rows, loteria=c.loteria, year=c.year)
    if not datos:
        return Respuesta(c.intencion, f"No hay sorteos registrados{_ambito(c)}.")

    if c.intencion == "top":
        top = stats.top_numeros(datos, c.cantidad)
        lineas = [f"{i}. {_fmt(t['numero'])} — {t['apariciones']} veces" for i, t in enumerate(top, 1)]
        texto = f"Números más salidos{_ambito(c)} ({len(datos)} sorteos):\n" + "\n".join(lineas)
        return Respuesta("top", texto, top)

    if c.intencion == "ultimos":
        ult = stats.ultimos(datos, c.cantidad if c.cantidad != 10 else 5)
        lineas = [f"{u['fecha']} · {u['loteria']}: " + " - ".join(_fmt(n) for n in u["numeros"]) for u in ult]
        return Respuesta("ultimos", f"Últimos resultados{_ambito(c)}:\n" + "\n".join(lineas), ult)

    if c.intencion == "combinaciones":
        comb = stats.combinaciones(datos, c.cantidad if c.cantidad != 10 else 5)
        lineas = [
            f"{i}. " + "-".join(_fmt(n) for n in x["combinacion"]) + f" — {x['apariciones']} veces"
            for i, x in enumerate(comb, 1)
        ]
        return Respuesta("combinaciones", f"Ternas más repetidas{_ambito(c)}:\n" + "\n".join(lineas), comb)

    if c.intencion == "atrasados":
        atr = stats.atrasados(datos, c.cantidad)
        lineas = [
            f"{i}. {_fmt(a['numero'])} — {a['sorteos_sin_salir']} sorteos sin salir"
            + (f" (última vez {a['ultima_fecha']})" if a["ultima_fecha"] else "")
            for i, a in enumerate(atr, 1)
        ]
        return Respuesta("atrasados", f"Números más atrasados{_ambito(c)}:\n" + "\n".join(lineas), atr)

    if c.intencion == "numero" and c.numero is not None:
        info = stats.apariciones_numero(datos, c.numero, limite=5)
        if not info["total"]:
            return Respuesta("numero", f"El {_fmt(c.numero)} no ha salido{_ambito(c)}.", info)
        p = info["posiciones"]
        recientes = "\n".join(f"• {s['fecha']} · {s['loteria']}" for s in info["sorteos"])
        texto = (
            f"El {_fmt(c.numero)} ha salido {info['total']} veces{_ambito(c)} "
            f"(1ro: {p['primer']}, 2do: {p['segundo']}, 3ro: {p['tercero']}).\n"
            f"Últimas apariciones:\n{recientes}"
        )
        return Respuesta("numero", texto, info)

    return Respuesta("desconocida", AYUDA)


def _instrucciones(borrador: str) -> str:
    return (
        "Eres el asistente de una app de estadísticas de loterías dominicanas. "
        "Responde en español, breve y claro, usando EXCLUSIVAMENTE los datos dados. "
        "No inventes números ni prometas ganancias; los sorteos son aleatorios. "
        f"Fecha de hoy: {date.today().isoformat()}.\n\nDATOS:\n{borrador}"
    )


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_gemini_transport = None  # los tests inyectan un httpx.MockTransport


async def _redactar_con_gemini(settings: Settings, pregunta: str, borrador: str) -> str | None:
    import httpx

    body = {
        "systemInstruction": {"parts": [{"text": _instrucciones(borrador)}]},
        "contents": [{"role": "user", "parts": [{"text": pregunta}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600},
    }
    try:
        async with httpx.AsyncClient(timeout=20, transport=_gemini_transport) as client:
            resp = await client.post(
                GEMINI_URL.format(model=settings.gemini_model),
                json=body,
                headers={"x-goog-api-key": settings.gemini_api_key or ""},
            )
        if resp.status_code != 200:
            log.warning("Gemini respondió %s; respuesta local.", resp.status_code)
            return None
        partes = resp.json()["candidates"][0]["content"]["parts"]
        texto = "".join(p.get("text", "") for p in partes).strip()
        return texto or None
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini no disponible (%s); respuesta local.", exc.__class__.__name__)
        return None


async def _redactar_con_openai(settings: Settings, pregunta: str, borrador: str) -> str | None:
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=15)
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            max_tokens=400,
            messages=[
                {"role": "system", "content": _instrucciones(borrador)},
                {"role": "user", "content": pregunta},
            ],
        )
        return (completion.choices[0].message.content or "").strip() or None
    except Exception as exc:  # noqa: BLE001
        log.warning("OpenAI no disponible (%s); respuesta local.", exc.__class__.__name__)
        return None


async def responder(pregunta: str, rows: list[Resultado], settings: Settings) -> Respuesta:
    pregunta = (pregunta or "").strip()[:MAX_PREGUNTA]
    if not pregunta:
        return Respuesta("vacia", "Escribe una pregunta. " + AYUDA)
    respuesta = responder_local(interpretar(pregunta), rows)
    proveedor = settings.ia_proveedor
    if proveedor and respuesta.intencion not in {"ayuda", "desconocida", "vacia"}:
        redactar = _redactar_con_gemini if proveedor == "gemini" else _redactar_con_openai
        redactada = await redactar(settings, pregunta, respuesta.texto)
        if redactada:
            respuesta.texto = redactada
    if respuesta.intencion not in {"ayuda", "desconocida", "vacia"}:
        respuesta.texto = f"{respuesta.texto}\n\n{DISCLAIMER}"
    return respuesta
