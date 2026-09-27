# Collector

El collector coordinará los scrapers de todos los juegos. Durante la primera fase, SuperKino se ejecuta directamente desde:

```powershell
python .\packages\games\superkino\sync.py --csv .\data\superkino\superkino_historico.csv --append-latest --backup-csv
```

La siguiente fase extraerá la lógica común de red, validación y fuentes hacia paquetes compartidos.
