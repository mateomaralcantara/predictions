# Predictions Monorepo

Plataforma unificada para resultados, scraping, analítica y predicciones heurísticas de loterías dominicanas.

## Estado

- SuperKino: activo, rango actual 1–84.
- Loto LEIDSA: activo, 6/40 + Más 1/12 + Súper Más 1/15.
- Loto Pool, Quiniela, Palé y otros: pendientes como módulos independientes.

## Comandos centrales

```powershell
npm run repo:status
npm run repo:doctor

npm run superkino:update
npm run superkino:predict
npm run superkino:all
npm run superkino:watch

npm run loto:update
npm run loto:predict
npm run loto:all
npm run loto:watch
```

## Loto LEIDSA

El CSV operativo vive en `data/loto/loto_historico.csv` y no se versiona en Git porque cambia con cada sorteo.

Formato:

```text
fecha,num_1,num_2,num_3,num_4,num_5,num_6,mas,super_mas
```

Probar dos fechas sin guardar:

```powershell
python .\packages\games\loto\sync.py `
  --csv .\data\loto\loto_historico.csv `
  --probe 2026-09-26 2026-09-30 `
  --timeout-s 10 `
  --attempts 2
```

Actualizar el histórico:

```powershell
npm run loto:update
```

Generar 8 jugadas:

```powershell
npm run loto:predict
```

Vigilar un resultado nuevo aproximadamente cada 90 segundos:

```powershell
npm run loto:watch
```

## SuperKino

```powershell
npm run superkino:update
npm run superkino:predict
```

> Los predictores son heurísticos. El histórico puede orientar criterios de selección, pero no aumenta la probabilidad matemática de una combinación individual en un sorteo justo.
