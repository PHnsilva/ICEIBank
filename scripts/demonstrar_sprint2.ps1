param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('transferencia','resiliencia','causal','adicional')]
    [string]$Cenario
)
$ErrorActionPreference = 'Stop'
$raizSprint = Split-Path -Parent $PSScriptRoot
$pythonSprint = Join-Path $raizSprint '.venv/Scripts/python.exe'
$pastaEvidencias = Join-Path $raizSprint 'evidencias/sprint2'
New-Item -ItemType Directory -Force -Path $pastaEvidencias | Out-Null
if (-not $env:RABBITMQ_URL_TESTES -or -not $env:RABBITMQ_MANAGEMENT_URL_TESTES) {
    throw 'Defina RABBITMQ_URL_TESTES e RABBITMQ_MANAGEMENT_URL_TESTES para o RabbitMQ do ensaio.'
}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
Push-Location -LiteralPath $raizSprint
try {
    Start-Transcript -LiteralPath (Join-Path $pastaEvidencias "$Cenario-terminal.txt") -Force | Out-Null
    Write-Host "ICEIBank Sprint 2 — cenário: $Cenario"
    Write-Host 'Data real da execução (Get-Date -Format o):'
    Get-Date -Format o
    & $pythonSprint -m scripts.demonstrar_sprint2 $Cenario 2>&1 |
        Tee-Object -FilePath (Join-Path $pastaEvidencias "$Cenario-saida.txt")
    if ($LASTEXITCODE -ne 0) { throw 'Demonstração falhou; não use esta execução como evidência.' }
} finally {
    Stop-Transcript | Out-Null
    Pop-Location
}
