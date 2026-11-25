<#
.SYNOPSIS
    Restaura de forma idempotente el snapshot semilla pre-defensa en giragroup_db.
.DESCRIPTION
    Lee POSTGRES_USER y POSTGRES_DB desde .env (sin credenciales hardcodeadas),
    recrea la base de datos en el contenedor giragroup_db y restaura
    backups/snapshot_pre_defensa.dump (~10 s).
#>
[CmdletBinding()]
param(
    [string]$DumpPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($DumpPath)) {
    $DumpPath = Join-Path $RepoRoot "backups\snapshot_pre_defensa.dump"
}

if (-not (Test-Path $DumpPath)) {
    Write-Error "No se encontró el archivo semilla: $DumpPath"
    exit 1
}

# Leer POSTGRES_USER y POSTGRES_DB desde .env si existe
$EnvFile = Join-Path $RepoRoot ".env"
$PgUser = "giragroup_user"
$PgDb = "giragroup_db"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*POSTGRES_USER\s*=\s*(.+?)\s*$') { $PgUser = $Matches[1].Trim('"').Trim("'") }
        if ($_ -match '^\s*POSTGRES_DB\s*=\s*(.+?)\s*$') { $PgDb = $Matches[1].Trim('"').Trim("'") }
    }
}

Write-Host "=== GiraGroup BI: Restauración rápida de semilla ===" -ForegroundColor Cyan
Write-Host "Archivo : $DumpPath"
Write-Host "Destino : contenedor giragroup_db -> BD '$PgDb' (usuario '$PgUser')"

$dbRunning = (docker inspect -f "{{.State.Running}}" giragroup_db 2>$null)
if ($dbRunning -ne "true") {
    Write-Host "Iniciando servicio db..."
    docker compose -f (Join-Path $RepoRoot "docker-compose.yml") up -d db | Out-Null
    Start-Sleep -Seconds 4
}

$t0 = Get-Date
Write-Host "Deteniendo conexiones activas y recreando BD '$PgDb'..."
docker exec giragroup_db psql -U $PgUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PgDb' AND pid <> pg_backend_pid();" | Out-Null
docker exec giragroup_db psql -U $PgUser -d postgres -c "DROP DATABASE IF EXISTS $PgDb;" | Out-Null
docker exec giragroup_db psql -U $PgUser -d postgres -c "CREATE DATABASE $PgDb;" | Out-Null

Write-Host "Copiando y restaurando snapshot..."
docker cp $DumpPath giragroup_db:/tmp/snapshot_pre_defensa.dump
docker exec giragroup_db pg_restore -U $PgUser -d $PgDb --no-owner --no-acl /tmp/snapshot_pre_defensa.dump
$restoreExit = $LASTEXITCODE
docker exec giragroup_db rm -f /tmp/snapshot_pre_defensa.dump | Out-Null

if ($restoreExit -gt 1) {
    Write-Error "pg_restore falló con código $restoreExit"
    exit $restoreExit
}

Write-Host "Reiniciando giragroup_api para limpiar cachés en memoria..."
docker restart giragroup_api | Out-Null

$elapsed = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
Write-Host "Verificando conteos restaurados..."
docker exec giragroup_db psql -U $PgUser -d $PgDb -c "SELECT (SELECT count(*) FROM fact_rendimiento_academico) AS rend_acad, (SELECT count(*) FROM fact_situacion_financiera) AS fin, (SELECT count(*) FROM fact_evaluacion_docente) AS eval_doc, (SELECT count(*) FROM fact_forecast) AS forecast, (SELECT count(*) FROM bi.ref_kpi) AS kpis_cmi;"
Write-Host "=== Semilla restaurada en ${elapsed} s ===" -ForegroundColor Green
