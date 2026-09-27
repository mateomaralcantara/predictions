$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

Write-Host "== 1) Reparando CSV ==" -ForegroundColor Cyan
python .\superkino_sync_v2.py --csv .\superkino_historico_limpio.csv --repair-csv --backup-csv

Write-Host "`n== 2) Rellenando faltantes hasta hoy ==" -ForegroundColor Cyan
python .\superkino_sync_v2.py --csv .\superkino_historico_limpio.csv --append-latest --skip-early-today --backup-csv

Write-Host "`n== 3) Generando 8 jugadas ==" -ForegroundColor Cyan
python .\superkino_predictor_v4.py --csv .\superkino_historico_limpio.csv --panels 8 --pick-size 10

Write-Host "`nListo." -ForegroundColor Green
