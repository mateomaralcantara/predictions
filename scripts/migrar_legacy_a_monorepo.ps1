param(
    [string]$LegacyRoot = "C:\\Users\\martin\\Desktop\\VSC\\APP\\predictions",
    [string]$MonorepoRoot = "C:\\Users\\martin\\Desktop\\VSC\\BestS\\predictions"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " MIGRACION LEGACY -> PREDICTIONS MONOREPO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path "$MonorepoRoot\\.git")) {
    throw "El destino no es el repo predictions: $MonorepoRoot"
}

if (-not (Test-Path $LegacyRoot)) {
    throw "No existe el proyecto anterior: $LegacyRoot"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $MonorepoRoot "_migration_backup_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null

$excludeDirs = @(
    ".git","node_modules",".next","dist","build","coverage",
    "__pycache__",".pytest_cache",".mypy_cache",".ruff_cache",
    "venv",".venv","env",".envdir"
)

function Copy-AppSafely {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Name
    )

    if (-not (Test-Path $Source)) {
        Write-Host "$Name no encontrado en $Source; se omite." -ForegroundColor Yellow
        return
    }

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    $note = Join-Path $Destination "README.md"
    if (Test-Path $note) {
        $backupName = $Name + "_README_before_migration.md"
        Copy-Item $note (Join-Path $backup $backupName) -Force
    }

    Write-Host "Migrando $Name..." -ForegroundColor Yellow

    $roboArgs = @(
        $Source,
        $Destination,
        "/E",
        "/COPY:DAT",
        "/DCOPY:DAT",
        "/R:2",
        "/W:1",
        "/NP",
        "/NFL",
        "/NDL",
        "/XD"
    ) + $excludeDirs

    & robocopy @roboArgs | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "Robocopy fallo migrando $Name. Codigo: $code"
    }

    Write-Host "$Name -> $Destination" -ForegroundColor Green
}

$frontendSource = Join-Path $LegacyRoot "frontend"
$frontendDest = Join-Path $MonorepoRoot "apps\\web"
Copy-AppSafely -Source $frontendSource -Destination $frontendDest -Name "frontend"

$backendSource = Join-Path $LegacyRoot "backend"
$backendDest = Join-Path $MonorepoRoot "apps\\api"
Copy-AppSafely -Source $backendSource -Destination $backendDest -Name "backend"

Write-Host ""
Write-Host "Verificando estructura..." -ForegroundColor Yellow
$doctor = Join-Path $MonorepoRoot "scripts\\monorepo.ps1"
powershell -ExecutionPolicy Bypass -File $doctor doctor

Write-Host ""
Write-Host "Migracion local completada." -ForegroundColor Green
Write-Host "Backup de notas previas: $backup" -ForegroundColor DarkGray
Write-Host ""
Write-Host "IMPORTANTE: revisa git status antes de hacer commit." -ForegroundColor Yellow
git -C $MonorepoRoot status --short
