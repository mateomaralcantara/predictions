param(
    [ValidateSet("status","doctor","superkino-update","superkino-predict","superkino-watch","superkino-all")]
    [string]$Command = "status"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Csv = Join-Path $Root "data\superkino\superkino_historico.csv"
$Sync = Join-Path $Root "packages\games\superkino\sync.py"
$Predictor = Join-Path $Root "packages\games\superkino\predictor.py"
$LegacyCsv = Join-Path $Root "apps\api\leidsa\superkino\superkino_historico.csv"

function Get-PythonCommand {
    # En este equipo "py" puede resolver a un launcher roto; preferimos python.
    foreach ($cmd in @("python", "py")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            & $cmd --version *> $null
            if ($LASTEXITCODE -eq 0) { return $cmd }
        }
    }
    throw "Python no esta disponible o no responde correctamente en PATH."
}

function Ensure-SuperKinoCsv {
    if (Test-Path $Csv) { return }

    $dataDir = Split-Path -Parent $Csv
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

    if (Test-Path $LegacyCsv) {
        Copy-Item -LiteralPath $LegacyCsv -Destination $Csv -Force
        Write-Host "CSV operativo creado desde copia legacy: $LegacyCsv" -ForegroundColor Yellow
        return
    }

    $header = "fecha," + ((1..20 | ForEach-Object { "num_$_" }) -join ",")
    Set-Content -LiteralPath $Csv -Value $header -Encoding UTF8
    Write-Host "CSV operativo nuevo creado: $Csv" -ForegroundColor Yellow
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
    Ensure-SuperKinoCsv

    Write-Host "SuperKino: reparando histórico..." -ForegroundColor Yellow
    & $Python $Sync --csv $Csv --repair-csv --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo repair-csv" }

    Write-Host "SuperKino: rellenando huecos desde 2020-01-01 hasta hoy..." -ForegroundColor Yellow
    & $Python $Sync --csv $Csv --sync-missing --start 2020-01-01 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo sync-missing" }
}

function Invoke-SuperKinoWatch {
    $Python = Get-PythonCommand
    Ensure-SuperKinoCsv
    & $Python $Sync --csv $Csv --watch-latest --poll-seconds 90 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo watch-latest" }
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
    "superkino-watch" { Invoke-SuperKinoWatch }
    "superkino-all" {
        Invoke-SuperKinoUpdate
        Invoke-SuperKinoPredict
    }
}
