param(
    [ValidateSet("status","doctor","superkino-update","superkino-predict","superkino-all")]
    [string]$Command = "status"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Csv = Join-Path $Root "data\superkino\superkino_historico.csv"
$Sync = Join-Path $Root "packages\games\superkino\sync.py"
$Predictor = Join-Path $Root "packages\games\superkino\predictor.py"

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) { return "py" }
    if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
    throw "Python no esta disponible en PATH."
}

function Show-Workspace {
    Write-Host ""
    Write-Host "PREDICTIONS MONOREPO" -ForegroundColor Cyan
    Write-Host "Root: $Root"
    Write-Host ""
    foreach ($p in @(
        "apps\web",
        "apps\api",
        "apps\collector",
        "apps\worker",
        "packages\core",
        "packages\sources",
        "packages\analytics",
        "packages\games\superkino",
        "data\superkino",
        "config",
        "infra",
        "tests"
    )) {
        $full = Join-Path $Root $p
        $state = if (Test-Path $full) { "OK" } else { "MISSING" }
        Write-Host ("{0,-34} {1}" -f $p, $state)
    }
    Write-Host ""
    git -C $Root branch --show-current
    git -C $Root log -1 --oneline
}

function Invoke-Doctor {
    Show-Workspace
    $Python = Get-PythonCommand
    Write-Host ""
    Write-Host "Python:" -ForegroundColor Yellow
    & $Python --version
    Write-Host "Git:" -ForegroundColor Yellow
    git --version

    foreach ($f in @($Sync,$Predictor,(Join-Path $Root "workspace.json"),(Join-Path $Root "package.json"))) {
        if (-not (Test-Path $f)) { throw "Falta archivo requerido: $f" }
    }

    & $Python -m py_compile $Sync
    & $Python -m py_compile $Predictor

    if (Test-Path $Csv) {
        Write-Host "CSV SuperKino: OK ($((Get-Item $Csv).Length) bytes)" -ForegroundColor Green
    } else {
        Write-Host "CSV SuperKino: NO ENCONTRADO" -ForegroundColor Yellow
    }

    Write-Host "Doctor: OK" -ForegroundColor Green
}

function Invoke-SuperKinoUpdate {
    $Python = Get-PythonCommand
    if (-not (Test-Path $Csv)) { throw "No existe $Csv" }
    & $Python $Sync --csv $Csv --repair-csv --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo repair-csv" }
    & $Python $Sync --csv $Csv --append-latest --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo append-latest" }
}

function Invoke-SuperKinoPredict {
    $Python = Get-PythonCommand
    if (-not (Test-Path $Csv)) { throw "No existe $Csv" }
    & $Python $Predictor --csv $Csv --panels 8 --pick-size 10
    if ($LASTEXITCODE -ne 0) { throw "Fallo predictor" }
}

switch ($Command) {
    "status" { Show-Workspace }
    "doctor" { Invoke-Doctor }
    "superkino-update" { Invoke-SuperKinoUpdate }
    "superkino-predict" { Invoke-SuperKinoPredict }
    "superkino-all" {
        Invoke-SuperKinoUpdate
        Invoke-SuperKinoPredict
    }
}
