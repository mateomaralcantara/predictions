# Datos de SuperKino

El CSV operativo se llama `superkino_historico.csv` y se mantiene fuera de Git porque cambia con cada sorteo.

Formato canónico:

```text
fecha,num_1,num_2,...,num_20
YYYY-MM-DD,1,2,...,84
```

## Regla vigente

SuperKinoTV selecciona 20 bolas y la regla actual usa números del **1 al 84**. El predictor conserva compatibilidad con el histórico antiguo 1..80, pero cuando detecta resultados con 81..84 modela la era de la regla actual por separado para no penalizar artificialmente los números nuevos.

## Operación

Desde la raíz del monorepo:

```powershell
npm run superkino:update
npm run superkino:predict
npm run superkino:all
npm run superkino:watch
```

`superkino:update` repara el CSV, recupera filas lógicas concatenadas cuando es posible y rellena huecos desde 2020-01-01 hasta hoy.

`superkino:watch` revisa periódicamente el resultado reciente y actualiza el CSV operativo cuando detecta un nuevo sorteo.

El CSV operativo y sus backups son datos mutables y no deben versionarse.
