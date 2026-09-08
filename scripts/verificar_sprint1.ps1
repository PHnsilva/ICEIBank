$ErrorActionPreference = 'Stop'
$raizSprint = Split-Path -Parent $PSScriptRoot
$pythonSprint = Join-Path $raizSprint '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonSprint)) {
    throw 'Prepare o ambiente .venv conforme README.md antes de verificar.'
}
$relatorioSprint = Join-Path $raizSprint 'evidencias/sprint1/verificacao.txt'
Push-Location -LiteralPath $raizSprint
try {
    # Transcript mínimo, sem variáveis de ambiente, senhas ou tokens.
    'PS> Get-Date -Format o' | Set-Content -LiteralPath $relatorioSprint -Encoding utf8
    Get-Date -Format o | Tee-Object -FilePath $relatorioSprint -Append
    'PS> python -m pytest agencia/tests tests/e2e -q --tb=short' | Tee-Object -FilePath $relatorioSprint -Append
    & $pythonSprint -m pytest agencia/tests tests/e2e -q --tb=short 2>&1 |
        Tee-Object -FilePath $relatorioSprint -Append
    $resultadoSprint = $LASTEXITCODE
    "Exit code: $resultadoSprint" | Tee-Object -FilePath $relatorioSprint -Append
    'PS> Get-Date -Format o' | Tee-Object -FilePath $relatorioSprint -Append
    Get-Date -Format o | Tee-Object -FilePath $relatorioSprint -Append
    if ($resultadoSprint -ne 0) { throw "Verificação falhou: $resultadoSprint" }
    'PS> git diff --check' | Tee-Object -FilePath $relatorioSprint -Append
    git -c core.safecrlf=false diff --check 2>&1 | Tee-Object -FilePath $relatorioSprint -Append
    if ($LASTEXITCODE -ne 0) { throw 'git diff --check falhou.' }
    'git diff --check: OK' | Tee-Object -FilePath $relatorioSprint -Append
} finally {
    Pop-Location
}
