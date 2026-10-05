$ErrorActionPreference = 'Stop'
$raizSprint = Split-Path -Parent $PSScriptRoot
$pythonSprint = Join-Path $raizSprint '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonSprint)) { throw 'Prepare o .venv conforme README.md.' }
if (-not $env:RABBITMQ_URL_TESTES) { throw 'Defina RABBITMQ_URL_TESTES para um ambiente exclusivo de testes.' }
$pastaEvidencias = Join-Path $raizSprint 'evidencias/sprint2'
New-Item -ItemType Directory -Force -Path $pastaEvidencias | Out-Null
$relatorioSprint = Join-Path $pastaEvidencias 'verificacao.txt'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $raizSprint
try {
    'Data real da verificação (Get-Date -Format o):' | Set-Content -LiteralPath $relatorioSprint -Encoding utf8
    Get-Date -Format o | Tee-Object -FilePath $relatorioSprint -Append
    & $pythonSprint -m pytest agencia/tests tests/e2e -q --tb=short 2>&1 | Tee-Object -FilePath $relatorioSprint -Append
    $resultadoSprint = $LASTEXITCODE
    "Exit code: $resultadoSprint" | Tee-Object -FilePath $relatorioSprint -Append
    if ($resultadoSprint -ne 0) { throw 'A verificação da Sprint 2 falhou.' }
    git -c core.safecrlf=false diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Há erros de formatação no diff.' }
    'git diff --check: OK' | Tee-Object -FilePath $relatorioSprint -Append
} finally { Pop-Location }
