# Predictions Monorepo

Plataforma unificada para resultados, scraping, analitica y predicciones heuristicas de loterias dominicanas.

## Arquitectura

```text
predictions/
|-- apps/
|   |-- web/                  # frontend real
|   |-- api/                  # backend/API real
|   |-- collector/            # coordinacion de scrapers
|   `-- worker/               # tareas programadas
|
|-- packages/
|   |-- core/                 # modelos, validacion y utilidades
|   |-- sources/              # fuentes externas
|   |-- analytics/            # estadistica y backtesting
|   `-- games/
|       `-- superkino/        # primer juego activo
|           |-- sync.py
|           `-- predictor.py
|
|-- data/
|   `-- superkino/            # CSV vivo, backups y exportaciones locales
|
|-- config/                   # configuracion compartida
|-- infra/                    # despliegue, workers, CI/CD
|-- tests/                    # pruebas integradas
|-- docs/                     # arquitectura y decisiones
|-- scripts/                  # automatizacion PowerShell
|
|-- workspace.json            # registro de apps y packages
|-- package.json              # comandos desde la raiz
|-- pyproject.toml            # tooling Python compartido
|-- requirements.txt
|-- .editorconfig
`-- .gitignore
```

## Apps vs Packages

**apps/** contiene procesos desplegables o ejecutables.

**packages/** contiene logica reutilizable. Un juego no debe duplicar scraping, validacion o analitica dentro del frontend/backend.

## Estado

- SuperKino: activo.
- frontend anterior: pendiente de importar desde la copia local real.
- backend anterior: pendiente de importar desde la copia local real.
- Loto, Loto Mas, Quiniela, Pale y otros: se agregaran como nuevos modulos bajo `packages/games`.

## Comando central

Desde la raiz:

```powershell
npm run repo:status
npm run repo:doctor
npm run superkino:update
npm run superkino:predict
npm run superkino:all
```

Tambien puede ejecutarse directamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\monorepo.ps1 doctor
```

## Migrar frontend y backend anteriores

El proyecto anterior detectado esta en:

```text
C:\Users\martin\Desktop\VSC\APP\predictions
```

El nuevo monorepo esta en:

```text
C:\Users\martin\Desktop\VSC\BestS\predictions
```

Para copiar de forma segura el frontend y backend reales al monorepo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\migrar_legacy_a_monorepo.ps1
```

El migrador excluye `.git`, `node_modules`, `.next`, builds, caches y entornos virtuales.

## SuperKino

Actualizar resultados:

```powershell
python .\packages\games\superkino\sync.py --csv .\data\superkino\superkino_historico.csv --append-latest --backup-csv
```

Generar 8 paneles:

```powershell
python .\packages\games\superkino\predictor.py --csv .\data\superkino\superkino_historico.csv --panels 8 --pick-size 10
```

> El predictor es heuristico. El historico puede orientar criterios de seleccion, pero no aumenta la probabilidad matematica de una combinacion individual en un sorteo justo.
