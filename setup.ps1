$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Find-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

$uv = Find-Uv
if ($null -eq $uv) {
    Write-Host "Instalando uv..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
    $uv = Find-Uv
}
if ($null -eq $uv) {
    throw "uv quedó instalado fuera de PATH. Abre otra terminal y repite el comando."
}

& $uv python install 3.13
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar Python 3.13 con uv." }

& $uv venv --python 3.13 --allow-existing .venv
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear o reutilizar .venv." }

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$requirements = Join-Path $PSScriptRoot "requirements.txt"
& $uv pip install --python $python -r $requirements
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }

Write-Host ""
Write-Host "Instalación lista. Ejecuta: powershell -ExecutionPolicy Bypass -File arrancar.ps1"
Write-Host "URL: http://127.0.0.1:8000"
Write-Host "Endpoints: http://127.0.0.1:8000/efecto"
Write-Host "           http://127.0.0.1:8000/salud"
Write-Host "           http://127.0.0.1:8000/docs"
