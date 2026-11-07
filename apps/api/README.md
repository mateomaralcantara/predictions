# API · FastAPI

Backend de resultados, estadísticas, chat, predicciones y pagos.

```bash
pip install -r ../../requirements-dev.txt
cp .env.example .env          # todo es opcional
python -m uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: <http://localhost:8000/docs>

## Estructura

| Módulo | Responsabilidad |
|---|---|
| `app/config.py` | Configuración desde `.env`. Ningún secreto en el código. |
| `app/repository.py` | Carga resultados de PostgreSQL o, si no está disponible, del CSV. Caché en memoria y limpieza de repeticiones del scraper. |
| `app/stats.py` | Estadísticas puras (top, últimos, atrasados, ternas, resumen). |
| `app/chat.py` | Interpreta preguntas con reglas. OpenAI (opcional) solo redacta. |
| `app/predictions.py` | Expone `packages/games/{loto,superkino}` con caché por sorteo. |
| `app/payments.py` | PayPal Orders v2, planes y límites por nivel. |
| `app/auth.py` · `app/cuentas.py` | Contraseñas (scrypt), JWT, niveles y activación de suscripciones. |
| `app/db.py` · `migrations/` | Modelos SQLAlchemy y migraciones Alembic (se aplican al arrancar). |
| `app/ratelimit.py` | Límite de peticiones por IP o usuario. |
| `app/cli.py` | `python -m app.cli migrar \| importar-csv \| crear-admin \| dar-plan`. |
| `app/routers/*` | Endpoints HTTP y WebSocket. |

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/registro` · `/api/auth/login` | Crea una cuenta o inicia sesión → `{token, usuario}` |
| GET | `/api/auth/yo` · `/api/auth/pagos` | Perfil, plan, límites e historial de pagos (requiere `Authorization: Bearer`) |
| POST | `/api/auth/password` | Cambia la contraseña |
| GET | `/api/health` | Estado, fuente de datos, sorteos cargados y descartados |
| GET | `/api/loterias` | Loterías disponibles con rango de fechas |
| GET | `/api/estadisticas/resumen?loteria=` | Último sorteo, más frecuente (30 días), más atrasado |
| GET | `/api/estadisticas/top?loteria=&year=&limite=` | Números más salidos |
| GET | `/api/estadisticas/ultimos?loteria=&limite=` | Últimos resultados |
| GET | `/api/estadisticas/atrasados?loteria=&limite=` | Números que más sorteos llevan sin salir |
| GET | `/api/estadisticas/combinaciones?loteria=&limite=` | Ternas más repetidas |
| GET | `/api/estadisticas/numero/{0-99}?loteria=` | Historial de un número |
| GET | `/api/predicciones/{loto\|superkino}?jugadas=1-10` | Jugadas heurísticas |
| POST | `/api/chat` `{pregunta}` · WS `/ws` | Asistente |
| GET | `/api/pagos/planes` | Planes y si los pagos están activos |
| POST | `/api/pagos/ordenes` `{plan}` | Crea una orden de PayPal ligada al usuario y devuelve `approve_url` |
| POST | `/api/pagos/ordenes/{id}/captura` | Verifica y captura el pago y activa la suscripción (idempotente) |
| POST | `/api/admin/scraping` · `/api/admin/recargar` | Requieren la cabecera `X-Admin-Token` (solo existen si `ADMIN_TOKEN` está definido) |

Se mantienen por compatibilidad: `/api/numeros-mas-salidores`, `/api/fechas-numero` y `/pregunta`.
