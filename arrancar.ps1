$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$activate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path -LiteralPath $activate)) {
    throw "No existe .venv. Ejecuta primero: powershell -ExecutionPolicy Bypass -File setup.ps1"
}

. $activate
$env:SIC_ESCENARIO = "synthetic/ihdp"

Write-Host "Escenario: $env:SIC_ESCENARIO"
Write-Host "URL: http://127.0.0.1:8000"
Write-Host "Endpoints: http://127.0.0.1:8000/efecto"
Write-Host "           http://127.0.0.1:8000/salud"
Write-Host "           http://127.0.0.1:8000/docs"
Write-Host "Detén el servicio con Ctrl-C."

& uvicorn servicio:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
