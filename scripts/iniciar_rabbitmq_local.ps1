param([string]$Diretorio = (Join-Path (Split-Path -Parent $PSScriptRoot) '.local/rabbitmq'))
$ErrorActionPreference = 'Stop'
$brokerLocal = [System.IO.Path]::GetFullPath($Diretorio)
New-Item -ItemType Directory -Force -Path $brokerLocal | Out-Null
# Distribuições oficiais portáteis: sem instalar serviço ou alterar PATH global.
$erlLocal = Join-Path $brokerLocal 'otp'
$serverLocal = Join-Path $brokerLocal 'server/rabbitmq_server-4.3.6'
if (-not (Test-Path -LiteralPath (Join-Path $erlLocal 'bin/erl.exe'))) {
    curl.exe -fL --silent --show-error -o (Join-Path $brokerLocal 'otp.zip') 'https://github.com/erlang/otp/releases/download/OTP-28.3/otp_win64_28.3.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Download do Erlang oficial falhou.' }
    Expand-Archive -LiteralPath (Join-Path $brokerLocal 'otp.zip') -DestinationPath $erlLocal
}
if (-not (Test-Path -LiteralPath (Join-Path $serverLocal 'sbin/rabbitmq-server.bat'))) {
    curl.exe -fL --silent --show-error -o (Join-Path $brokerLocal 'rabbitmq.zip') 'https://github.com/rabbitmq/rabbitmq-server/releases/download/v4.3.6/rabbitmq-server-windows-4.3.6.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Download do RabbitMQ oficial falhou.' }
    Expand-Archive -LiteralPath (Join-Path $brokerLocal 'rabbitmq.zip') -DestinationPath (Join-Path $brokerLocal 'server')
}
$env:ERLANG_HOME = $erlLocal
$env:RABBITMQ_BASE = Join-Path $brokerLocal 'runtime'
$env:RABBITMQ_CONFIG_FILE = Join-Path $brokerLocal 'rabbitmq'
$env:RABBITMQ_ENABLED_PLUGINS_FILE = Join-Path $brokerLocal 'enabled_plugins'
$env:RABBITMQ_NODENAME = 'iceibank_sprint2@localhost'
$env:ERL_FLAGS = '-setcookie ICEIBANK_SPRINT2_LOCAL +S 2:2'
New-Item -ItemType Directory -Force -Path $env:RABBITMQ_BASE | Out-Null
$env:ERL_CRASH_DUMP = Join-Path $env:RABBITMQ_BASE 'erl_crash.dump'
@('listeners.tcp.1 = 127.0.0.1:5672','management.tcp.ip = 127.0.0.1','management.tcp.port = 15672',
  'distribution.listener.interface = 127.0.0.1') | Set-Content -LiteralPath "$($env:RABBITMQ_CONFIG_FILE).conf" -Encoding ascii
'[rabbitmq_management].' | Set-Content -LiteralPath $env:RABBITMQ_ENABLED_PLUGINS_FILE -Encoding ascii
& (Join-Path $serverLocal 'sbin/rabbitmq-server.bat')
if ($LASTEXITCODE -ne 0) { throw 'RabbitMQ local não iniciou.' }
