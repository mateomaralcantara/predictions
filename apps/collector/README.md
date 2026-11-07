# Collector

`tradicionales.py` mantiene `data/tradicionales/resultados_tradicionales.csv`.

```bash
python apps/collector/tradicionales.py --help
```

Lo ejecuta cada día `.github/workflows/datos.yml`. El parser vive en `packages/sources/loteriasdominicanas.py` y se prueba con HTML de ejemplo en `tests/fixtures/`.
