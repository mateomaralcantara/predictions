# Datos de SuperKino

El CSV operativo se llama `superkino_historico.csv` y se mantiene fuera de Git porque cambia con cada sorteo.

Formato canónico:

```text
fecha,num_1,num_2,...,num_20
YYYY-MM-DD,1,2,...,80
```

El sincronizador crea/repara el archivo y mantiene backups. Más adelante la fuente principal de persistencia será la base de datos y el CSV quedará como importación/exportación y respaldo.
