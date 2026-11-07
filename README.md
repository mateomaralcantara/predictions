# Predictions RD

Plataforma de resultados, estadísticas y jugadas heurísticas de loterías dominicanas.

- **Web** (`apps/web`): React 19, Vite, Tailwind y Recharts. Responsive y accesible.
- **API** (`apps/api`): FastAPI. Usa PostgreSQL si está disponible y, si no, el CSV histórico.
- **Juegos** (`packages/games`): sincronizadores y predictores de Loto LEIDSA (6/40 + Más + Súper Más) y SuperKino (1–84).

[![CI](https://github.com/mateomaralcantara/predictions/actions/workflows/ci.yml/badge.svg)](https://github.com/mateomaralcantara/predictions/actions/workflows/ci.yml)

## Inicio rápido

Requisitos: Python 3.11+ y Node 20+.

```bash
npm install
npm run api:install
```

```bash
npm run api:dev        # API en http://localhost:8000 (docs en /docs)
```

```bash
npm run dev            # Web en http://localhost:5174
```

Funciona sin configurar nada: sin base de datos usa el CSV, sin OpenAI el chat responde con reglas locales y sin PayPal los planes se muestran como «Próximamente». Para activar cada servicio, copia `apps/api/.env.example` a `apps/api/.env`.

## Calidad

```bash
npm run check          # ruff + eslint + pytest + build
```

CI (GitHub Actions) ejecuta lint, formato, tests y build en cada push y PR.

## Datos

| Juego | Archivo operativo (no versionado) | Copia de respaldo en el repo |
|---|---|---|
| Tradicionales | `data/tradicionales/resultados_tradicionales.csv` | `apps/api/loterias/resultados_tradicionales_2010_a_hoy.csv` |
| Loto | `data/loto/loto_historico.csv` | `apps/api/leidsa/lotto/loto_leidsa.csv` |
| SuperKino | `data/superkino/superkino_historico.csv` | `apps/api/leidsa/superkino/superkino_historico.csv` |

La API usa el archivo operativo si existe y, si no, la copia de respaldo. También se pueden fijar las rutas con `RESULTADOS_CSV`, `LOTO_CSV` y `SUPERKINO_CSV`.

**Calidad del histórico.** Al cargar los datos, la API descarta los sorteos que repiten exactamente el resultado anterior de la misma lotería. Es la huella de un scraper que guardó la misma página varios días seguidos (por ejemplo, Nacional, Leidsa y Loteka entre enero y septiembre de 2011). En total se descartan unos 1.600 registros; el número aparece en `/api/health`. Además, el CSV tradicional **no tiene datos entre agosto de 2021 y diciembre de 2024**, y la web avisa de la fecha del último dato.

## Operación (Windows / PowerShell)

```powershell
npm run superkino:update; npm run superkino:predict
npm run loto:update;      npm run loto:predict
npm run loto:watch
```

En Linux/macOS: `npm run loto:predict:py` / `npm run superkino:predict:py`.

## Juego responsable

Los predictores son heurísticos. El histórico sirve para elegir criterios de selección, pero **no aumenta la probabilidad matemática** de ninguna combinación en un sorteo justo. Es una herramienta informativa para mayores de 18 años.
