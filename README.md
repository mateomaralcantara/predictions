# Predictions

Monorepo para resultados, sincronización, analítica y predicciones heurísticas de loterías dominicanas.

## Estado de la migración

SuperKino ya está incorporado como primer módulo. El frontend y backend anteriores **no se han recreado**: sus carpetas están reservadas y se migrarán desde los archivos reales para conservar comportamiento, rutas y configuración.

## Estructura

- `apps/web` — frontend existente (pendiente de importar).
- `apps/api` — backend/API existente (pendiente de importar).
- `apps/collector` — coordinación de scrapers.
- `apps/worker` — tareas recurrentes.
- `packages/core` — lógica compartida.
- `packages/sources` — adaptadores de fuentes.
- `packages/analytics` — estadísticas/backtesting compartido.
- `packages/games/superkino` — sincronizador y predictor actuales.
- `data/superkino` — datos locales/exportaciones; el CSV vivo no se versiona.
- `scripts` — automatización local.

## Instalación Python

```powershell
python -m pip install -r .\requirements.txt
```

## SuperKino

Actualizar resultados:

```powershell
python .\packages\games\superkino\sync.py --csv .\data\superkino\superkino_historico.csv --append-latest --backup-csv
```

Rellenar huecos históricos:

```powershell
python .\packages\games\superkino\sync.py --csv .\data\superkino\superkino_historico.csv --sync-missing --start 2020-01-01 --backup-csv
```

Vigilar nuevos resultados/cambios:

```powershell
python .\packages\games\superkino\sync.py --csv .\data\superkino\superkino_historico.csv --watch-latest --poll-seconds 90 --backup-csv
```

Generar 8 paneles:

```powershell
python .\packages\games\superkino\predictor.py --csv .\data\superkino\superkino_historico.csv --panels 8 --pick-size 10
```

Flujo local completo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\actualizar_superkino.ps1
```

> El predictor es heurístico. Organiza combinaciones usando el histórico, pero no aumenta la probabilidad matemática de una combinación individual en un sorteo justo.

Ver `docs/ARCHITECTURE.md` para la arquitectura objetivo.
