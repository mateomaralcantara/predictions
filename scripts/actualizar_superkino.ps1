$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Csv = Join-Path $Root "data\superkino\superkino_historico.csv"
$Sync = Join-Path $Root "packages\games\superkino\sync.py"
$Predictor = Join-Path $Root "packages\games\superkino\predictor.py"

Write-Host "== SuperKino: reparar/auditar CSV ==" -ForegroundColor Cyan
python $Sync --csv $Csv --repair-csv --backup-csv
if ($LASTEXITCODE -ne 0) { throw "Fallo reparando el CSV." }

Write-Host ""
Write-Host "== SuperKino: actualizar hasta hoy ==" -ForegroundColor Cyan
python $Sync --csv $Csv --append-latest --backup-csv
if ($LASTEXITCODE -ne 0) { throw "Fallo sincronizando resultados." }

Write-Host ""
Write-Host "== SuperKino: generar 8 paneles ==" -ForegroundColor Cyan
python $Predictor --csv $Csv --panels 8 --pick-size 10
if ($LASTEXITCODE -ne 0) { throw "Fallo ejecutando el predictor." }

Write-Host ""
Write-Host "Listo." -ForegroundColor Green
