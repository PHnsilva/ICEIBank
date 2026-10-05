param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('transferencia','resiliencia','causal','adicional')]
    [string]$Cenario
)
$ErrorActionPreference = 'Stop'
$raizSprint = Split-Path -Parent $PSScriptRoot
$pythonSprint = Join-Path $raizSprint '.venv/Scripts/python.exe'
$pastaEvidencias = Join-Path $raizSprint 'evidencias/sprint2'
$caminhoTranscript = Join-Path $pastaEvidencias "$Cenario-terminal.txt"
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
    Start-Transcript -LiteralPath $caminhoTranscript -Force | Out-Null
    Write-Host "ICEIBank Sprint 2 — cenário: $Cenario"
    Write-Host 'Data real da execução (Get-Date -Format o):'
    Get-Date -Format o
    & $pythonSprint -m scripts.demonstrar_sprint2 $Cenario 2>&1 |
        Tee-Object -FilePath (Join-Path $pastaEvidencias "$Cenario-saida.txt")
    if ($LASTEXITCODE -ne 0) { throw 'Demonstração falhou; não use esta execução como evidência.' }
} finally {
    Stop-Transcript | Out-Null
    # O cabeçalho nativo inclui espaços finais em campos vazios; remover apenas
    # whitespace não altera comandos, datas ou resultados do transcript real.
    $textoTranscript = [System.IO.File]::ReadAllText($caminhoTranscript)
    $textoTranscript = [regex]::Replace($textoTranscript, '[ \t]+(?=\r?$)', '', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    [System.IO.File]::WriteAllText($caminhoTranscript, $textoTranscript, [System.Text.UTF8Encoding]::new($false))
    Pop-Location
}
