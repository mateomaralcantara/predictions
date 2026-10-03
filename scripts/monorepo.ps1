param(
    [ValidateSet(
        "status","doctor",
        "superkino-update","superkino-predict","superkino-watch","superkino-all",
        "loto-update","loto-predict","loto-watch","loto-all"
    )]
    [string]$Command = "status"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$SuperKinoCsv = Join-Path $Root "data\superkino\superkino_historico.csv"
$SuperKinoSync = Join-Path $Root "packages\games\superkino\sync.py"
$SuperKinoPredictor = Join-Path $Root "packages\games\superkino\predictor.py"
$LegacySuperKinoCsv = Join-Path $Root "apps\api\leidsa\superkino\superkino_historico.csv"

$LotoCsv = Join-Path $Root "data\loto\loto_historico.csv"
$LotoSync = Join-Path $Root "packages\games\loto\sync.py"
$LotoPredictor = Join-Path $Root "packages\games\loto\predictor.py"
$LegacyLotoCandidates = @(
    (Join-Path $Root "apps\api\leidsa\loto\loto_historico.csv"),
    (Join-Path $Root "apps\api\leidsa\loto_historico.csv")
)

function Get-PythonCommand {
    foreach ($cmd in @("python", "py")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            & $cmd --version *> $null
            if ($LASTEXITCODE -eq 0) { return $cmd }
        }
    }
    throw "Python no esta disponible o no responde correctamente en PATH."
}

function Ensure-SuperKinoCsv {
    if (Test-Path $SuperKinoCsv) { return }
    $dataDir = Split-Path -Parent $SuperKinoCsv
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    if (Test-Path $LegacySuperKinoCsv) {
        Copy-Item -LiteralPath $LegacySuperKinoCsv -Destination $SuperKinoCsv -Force
        Write-Host "CSV SuperKino creado desde copia legacy: $LegacySuperKinoCsv" -ForegroundColor Yellow
        return
    }
    $header = "fecha," + ((1..20 | ForEach-Object { "num_$_" }) -join ",")
    Set-Content -LiteralPath $SuperKinoCsv -Value $header -Encoding UTF8
    Write-Host "CSV SuperKino nuevo creado: $SuperKinoCsv" -ForegroundColor Yellow
}

function Ensure-LotoCsv {
    if (Test-Path $LotoCsv) { return }
    $dataDir = Split-Path -Parent $LotoCsv
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    foreach ($candidate in $LegacyLotoCandidates) {
        if (Test-Path $candidate) {
            Copy-Item -LiteralPath $candidate -Destination $LotoCsv -Force
            Write-Host "CSV Loto creado desde copia legacy: $candidate" -ForegroundColor Yellow
            return
        }
    }
    $header = "fecha,num_1,num_2,num_3,num_4,num_5,num_6,mas,super_mas"
    Set-Content -LiteralPath $LotoCsv -Value $header -Encoding UTF8
    Write-Host "CSV Loto nuevo creado: $LotoCsv" -ForegroundColor Yellow
}

function Show-Workspace {
    Write-Host ""
    Write-Host "PREDICTIONS MONOREPO" -ForegroundColor Cyan
    Write-Host "Root: $Root"
    Write-Host ""
    foreach ($p in @(
        "apps\web", "apps\api", "apps\collector", "apps\worker",
        "packages\core", "packages\sources", "packages\analytics",
        "packages\games\superkino", "packages\games\loto",
        "data\superkino", "data\loto", "config", "infra", "tests"
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

    foreach ($f in @(
        $SuperKinoSync, $SuperKinoPredictor,
        $LotoSync, $LotoPredictor,
        (Join-Path $Root "workspace.json"), (Join-Path $Root "package.json")
    )) {
        if (-not (Test-Path $f)) { throw "Falta archivo requerido: $f" }
    }

    & $Python -m py_compile $SuperKinoSync
    & $Python -m py_compile $SuperKinoPredictor
    & $Python -m py_compile $LotoSync
    & $Python -m py_compile $LotoPredictor

    if (Test-Path $SuperKinoCsv) {
        Write-Host "CSV SuperKino: OK ($((Get-Item $SuperKinoCsv).Length) bytes)" -ForegroundColor Green
    } else {
        Write-Host "CSV SuperKino: NO ENCONTRADO" -ForegroundColor Yellow
    }
    if (Test-Path $LotoCsv) {
        Write-Host "CSV Loto: OK ($((Get-Item $LotoCsv).Length) bytes)" -ForegroundColor Green
    } else {
        Write-Host "CSV Loto: NO ENCONTRADO" -ForegroundColor Yellow
    }

    Write-Host "Doctor: OK" -ForegroundColor Green
}

function Invoke-SuperKinoUpdate {
    $Python = Get-PythonCommand
    Ensure-SuperKinoCsv
    Write-Host "SuperKino: reparando historico..." -ForegroundColor Yellow
    & $Python $SuperKinoSync --csv $SuperKinoCsv --repair-csv --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo repair-csv SuperKino" }
    Write-Host "SuperKino: rellenando huecos desde 2020-01-01 hasta hoy..." -ForegroundColor Yellow
    & $Python $SuperKinoSync --csv $SuperKinoCsv --sync-missing --start 2020-01-01 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo sync-missing SuperKino" }
}

function Invoke-SuperKinoWatch {
    $Python = Get-PythonCommand
    Ensure-SuperKinoCsv
    & $Python $SuperKinoSync --csv $SuperKinoCsv --watch-latest --poll-seconds 90 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo watch-latest SuperKino" }
}

function Invoke-SuperKinoPredict {
    $Python = Get-PythonCommand
    if (-not (Test-Path $SuperKinoCsv)) { throw "No existe $SuperKinoCsv" }
    & $Python $SuperKinoPredictor --csv $SuperKinoCsv --panels 8 --pick-size 10
    if ($LASTEXITCODE -ne 0) { throw "Fallo predictor SuperKino" }
}

function Invoke-LotoUpdate {
    $Python = Get-PythonCommand
    Ensure-LotoCsv
    Write-Host "Loto: reparando historico 6/40 + Mas + Super Mas..." -ForegroundColor Yellow
    & $Python $LotoSync --csv $LotoCsv --repair-csv --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo repair-csv Loto" }
    Write-Host "Loto: rellenando sorteos miercoles/sabado desde 2026-01-01..." -ForegroundColor Yellow
    & $Python $LotoSync --csv $LotoCsv --sync-missing --start 2026-01-01 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo sync-missing Loto" }
}

function Invoke-LotoWatch {
    $Python = Get-PythonCommand
    Ensure-LotoCsv
    & $Python $LotoSync --csv $LotoCsv --watch-latest --poll-seconds 90 --backup-csv
    if ($LASTEXITCODE -ne 0) { throw "Fallo watch-latest Loto" }
}

function Invoke-LotoPredict {
    $Python = Get-PythonCommand
    if (-not (Test-Path $LotoCsv)) { throw "No existe $LotoCsv" }
    & $Python $LotoPredictor --csv $LotoCsv --panels 8
    if ($LASTEXITCODE -ne 0) { throw "Fallo predictor Loto" }
}

switch ($Command) {
    "status" { Show-Workspace }
    "doctor" { Invoke-Doctor }
    "superkino-update" { Invoke-SuperKinoUpdate }
    "superkino-predict" { Invoke-SuperKinoPredict }
    "superkino-watch" { Invoke-SuperKinoWatch }
    "superkino-all" { Invoke-SuperKinoUpdate; Invoke-SuperKinoPredict }
    "loto-update" { Invoke-LotoUpdate }
    "loto-predict" { Invoke-LotoPredict }
    "loto-watch" { Invoke-LotoWatch }
    "loto-all" { Invoke-LotoUpdate; Invoke-LotoPredict }
}
