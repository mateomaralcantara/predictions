# Loterías tradicionales

`resultados_tradicionales.csv`: `id?, fecha, loteria, primer, segundo, tercero`.

Lo actualiza el workflow **Actualizar datos** (`.github/workflows/datos.yml`) cada día con
`apps/collector/tradicionales.py`. La API descarta automáticamente las repeticiones
consecutivas idénticas heredadas de scrapers antiguos.
