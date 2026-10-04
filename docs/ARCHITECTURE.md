# Arquitectura objetivo

```text
apps/
  web/        frontend
  api/        backend/API
  collector/  coordinación de scrapers
  worker/     tareas programadas

packages/
  core/       modelos, fechas, validación, persistencia
  sources/    adaptadores por fuente
  analytics/  estadísticas y backtesting compartido
  games/      reglas y lógica específica por juego

data/         datos locales de desarrollo/exportación
scripts/      operaciones locales
```

## Principios

1. El frontend no scrapea ni conoce selectores HTML.
2. El collector obtiene datos y los valida antes de persistirlos.
3. Cada juego declara su propia mecánica; no se fuerza el modelo de SuperKino sobre Loto/Quiniela.
4. Los históricos mutables no son la fuente de verdad de Git.
5. La migración del frontend/backend existente se hará desde sus archivos reales, no recreándolos por suposición.
6. Las predicciones son heurísticas y no cambian la probabilidad matemática de una combinación en un sorteo justo.
