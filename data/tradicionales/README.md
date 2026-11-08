# Loterías tradicionales

`resultados_tradicionales.csv`: `id?, fecha, loteria, primer, segundo, tercero`.

Lo actualiza el workflow **Actualizar datos** (`.github/workflows/datos.yml`) cada día con
`apps/collector/tradicionales.py`.

Fuente por defecto: **labanca.do** (páginas por fecha desde el 2026-02-12; 14 loterías).
Para fechas anteriores: `--fuente loteriasdominicanas --rellenar-huecos` (bloquea algunas redes).
Florida, New York y La Suerte solo se actualizan con loteriasdominicanas.com. La API descarta automáticamente las repeticiones
consecutivas idénticas heredadas de scrapers antiguos.
