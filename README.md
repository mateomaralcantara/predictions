# Predictions RD

Plataforma de resultados, estadísticas y jugadas heurísticas de loterías dominicanas, con cuentas de usuario y planes de pago.

[![CI](https://github.com/mateomaralcantara/predictions/actions/workflows/ci.yml/badge.svg)](https://github.com/mateomaralcantara/predictions/actions/workflows/ci.yml)
[![Datos](https://github.com/mateomaralcantara/predictions/actions/workflows/datos.yml/badge.svg)](https://github.com/mateomaralcantara/predictions/actions/workflows/datos.yml)

| Pieza | Tecnología | Qué hace |
|---|---|---|
| `apps/web` | React 19, Vite, Tailwind, Recharts | Estadísticas, explorador, predicciones, asistente, cuentas y pagos |
| `apps/api` | FastAPI, SQLAlchemy, Alembic | API, autenticación JWT, suscripciones, PayPal, límites por plan |
| `apps/collector` | Python | Recolector diario de loterías tradicionales con protección contra datos obsoletos |
| `packages/games` | Python, NumPy | Sincronización y predictores de Loto LEIDSA y SuperKino |
| `data/` | CSV versionados | Histórico; lo actualiza un bot cada día |

## Inicio rápido (desarrollo)

Requisitos: Python 3.11+ y Node 20+.

```bash
npm install && npm run api:install
```

```bash
npm run api:dev        # API en http://localhost:8000 (docs en /docs)
```

```bash
npm run dev            # Web en http://localhost:5174
```

### Configuración: un solo `.env.local`

Todas las claves van en **`.env.local`**, en la raíz del repo. Lo leen la API y la web, y Git lo ignora. La plantilla comentada es [`.env.example`](.env.example).

```bash
npm run setup     # asistente: pide cada clave sin mostrarla, genera SECRET_KEY y prueba Gemini y la base de datos
```

| Variable | Para qué | Dónde conseguirla |
|---|---|---|
| `GEMINI_API_KEY` | Asistente con Gemini (tiene prioridad sobre OpenAI) | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `SUPABASE_DB_URL` | Cuentas, pagos e histórico en Supabase (PostgreSQL) | Supabase → Project Settings → Database → Connection string (URI) |
| `PAYPAL_CLIENT_ID` / `PAYPAL_SECRET` | Cobro de planes | [PayPal Developer](https://developer.paypal.com/dashboard/applications) |
| `SECRET_KEY` | Firma de sesiones (`npm run setup` la genera) | — |

Prioridad: variables del sistema > `.env.local` > `apps/api/.env.local` > `apps/api/.env` (heredado) > `.env`. Solo las variables con prefijo `VITE_` llegan al navegador: nunca pongas secretos con ese prefijo.

Supabase funciona con la conexión directa, el *session pooler* (5432) y el *transaction pooler* (6543). La app activa SSL y desactiva las sentencias preparadas cuando hacen falta. Para subir el histórico a Supabase: `npm run cli -- importar-csv`.

¿Algo no arranca? Ejecuta `npm run doctor`: revisa Python, las dependencias, qué archivo `.env` se usa, los puertos y los datos; prueba la clave de Gemini y la conexión a la base de datos; arranca la API en memoria y te dice qué falla.

Funciona sin configurar nada: usa SQLite para las cuentas y los CSV para el histórico. Sin Gemini ni OpenAI, el chat responde con reglas locales; sin PayPal, los planes aparecen como «Próximamente».

## Producción con Docker

```bash
cp .env.docker.example .env      # define POSTGRES_PASSWORD y SECRET_KEY
```

```bash
docker compose up -d --build     # web en http://localhost:8080
```

```bash
docker compose exec api python -m app.cli importar-csv        # histórico a PostgreSQL
```

```bash
docker compose exec api python -m app.cli crear-admin tu@correo.com
```

Las migraciones se aplican solas al arrancar la API. La web (nginx) sirve el frontend y redirige `/backend` a la API, así que todo funciona en un único dominio.

### Desplegar en la nube (Render, Railway, Fly…)

1. **PostgreSQL** gestionado: copia su URL en `DATABASE_URL` (se aceptan `postgres://` y `postgresql://`).
2. **API**: servicio Docker con `apps/api/Dockerfile` (contexto: raíz del repo). Variables: `ENVIRONMENT=production`, `SECRET_KEY`, `DATABASE_URL`, `FRONTEND_URL`, `CORS_ORIGINS` y, cuando los tengas, `PAYPAL_*` y `OPENAI_API_KEY`.
3. **Web**: servicio Docker con `apps/web/Dockerfile` y `API_UPSTREAM=https://tu-api...`. Alternativa: sitio estático (Vercel, Netlify) con `VITE_API_URL=https://tu-api...`.
4. En GitHub, añade los secretos `DATABASE_URL` y `SECRET_KEY` para que el bot de datos importe a PostgreSQL cada día.
5. En PayPal, pasa de *sandbox* a *live* cambiando `PAYPAL_BASE_URL=https://api-m.paypal.com`.

## Cuentas y planes

| Plan | Precio (30 días) | Jugadas por juego | Historial por número | Asistente |
|---|---|---|---|---|
| Gratis | $0 | 2 | 10 | 10/min |
| Explorador | $9.99 | 5 | 50 | 20/min |
| Platinum | $29.99 | 10 | completo | 40/min |
| Oráculo | $59.99 | 10 | completo | 60/min |

- Es un pago único por 30 días, sin renovación automática. Si se renueva el mismo plan, los días se suman.
- El servidor fija el precio. Al capturar el pago se verifica que la orden sea del usuario y que el estado, el monto, la moneda y el plan coincidan. Recargar la página de éxito no cobra dos veces.
- Las contraseñas se guardan con scrypt, la sesión usa JWT (7 días) y hay límite de intentos en login y registro, y de peticiones en el chat.

Administración:

```bash
npm run cli -- --help    # migrar · importar-csv · crear-admin · dar-plan (desde la raíz)
```

## Datos

El workflow **Actualizar datos** corre cada día a las 23:17 (hora de RD) y también se puede lanzar a mano desde *Actions*. En cada ejecución:

- recoge los resultados tradicionales nuevos y rellena hasta 400 días de huecos (el hueco de agosto 2021 – diciembre 2024 se completa en unas 4 ejecuciones);
- sincroniza Loto y SuperKino;
- valida los datos con los tests y hace commit en `data/`;
- si existe el secreto `DATABASE_URL`, importa los resultados a PostgreSQL.

**Calidad de los datos.** El sitio de origen devuelve el *último* resultado cuando un día no tiene datos, y eso generó miles de registros falsos en el pasado. Ahora:

1. el recolector descarta los bloques cuya fecha no coincide con la pedida y los días que repiten el último resultado guardado;
2. la API descarta al cargar las repeticiones consecutivas idénticas (unos 1.600 registros heredados, visibles en `/api/health`).

## Calidad

```bash
npm run check     # ruff + eslint + pytest + vitest + build
```

El CI ejecuta lint y formato, pytest (con SQLite y con PostgreSQL), vitest, el build de la web y el build de las dos imágenes Docker.

## Juego responsable

Los predictores son heurísticos. El histórico sirve para elegir criterios de selección, pero **no aumenta la probabilidad matemática** de ninguna combinación en un sorteo justo. Los planes dan acceso a más análisis, no a mejores probabilidades. Solo para mayores de 18 años.
