$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

Write-Host "== 1) Reparando CSV ==" -ForegroundColor Cyan
python .\superkino_sync.py --csv .\superkino_historico.csv --repair-csv --backup-csv
if ($LASTEXITCODE -ne 0) { throw "Fallo reparando CSV" }

Write-Host "`n== 2) Rellenando huecos 2020 -> hoy ==" -ForegroundColor Cyan
python .\superkino_sync.py --csv .\superkino_historico.csv --sync-missing --start 2020-01-01 --backup-csv
if ($LASTEXITCODE -ne 0) { throw "Fallo sincronizando SuperKino" }

Write-Host "`n== 3) Generando 8 jugadas con regla 1..84 ==" -ForegroundColor Cyan
python .\superkino_predictor.py --csv .\superkino_historico.csv --panels 8 --pick-size 10
if ($LASTEXITCODE -ne 0) { throw "Fallo predictor SuperKino" }

Write-Host "`nSuperKino actualizado y predictor ejecutado." -ForegroundColor Green
