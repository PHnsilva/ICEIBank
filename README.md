# ICEIBank

Projeto acadêmico de sistema bancário distribuído desenvolvido em Python com FastAPI.

> Estado atual: implementação incremental da Sprint 1 na branch `sprint1/desenvolvimento`, limitada às seções 1 a 10.

O particionamento usa a regra `id_conta % 3`. O deslocamento pessoal 78 define o
seguinte mapeamento:

| Agência | Porta | URL |
| ---: | ---: | --- |
| 0 | 4078 | `http://localhost:4078` |
| 1 | 4079 | `http://localhost:4079` |
| 2 | 4080 | `http://localhost:4080` |

## Preparação no Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r agencia\requirements.txt
python -m pytest agencia\tests -q
```

## Execução das agências

Abra três terminais na pasta `agencia` e execute um comando em cada terminal:

```powershell
$env:AGENCIA_ID="0"; python executar.py
$env:AGENCIA_ID="1"; python executar.py
$env:AGENCIA_ID="2"; python executar.py
```

Cada processo mantém suas contas somente em memória. Reiniciar uma agência apaga
suas contas, mas os logs JSONL já gravados permanecem no diretório `agencia/data`.

## API de contas

- `POST /contas` — cria uma conta com `{"id": 0, "nomeAluno": "Ana", "saldoInicial": 100}`.
- `GET /contas/{id}` — consulta uma conta da agência atual.
- `POST /contas/{id}/depositar` — deposita com `{"valor": 25}`.
- `POST /contas/{id}/sacar` — saca com `{"valor": 10}`.
- `POST /transferencias` — transfere com `{"idOrigem": 0, "idDestino": 1, "valor": 30}`.
- `POST /contas/{id}/creditar-remoto` — uso direto entre agências com
  `{"valor": 30, "timestampLamport": 3, "origemAgencia": 0}`.

Os valores monetários usam `Decimal` internamente e são devolvidos com duas casas decimais.

## Limitação conhecida das transferências remotas

A origem é debitada antes do contato HTTP com o destino. Se a agência remota estiver
indisponível ou rejeitar o crédito, a API devolve HTTP 502 e registra
`TRANSFERENCIA_FALHOU`, mas não restaura o débito. A inconsistência é intencional nesta
etapa e será tratada somente na Sprint 4; ainda não existem 2PC, Saga, repetição,
compensação ou idempotência.

## Linha do tempo unificada

Depois de executar operações nas agências, mescle todos os arquivos JSONL a partir da
pasta `agencia`:

```powershell
python mesclar_logs.py
```

O script ordena primariamente pelo timestamp Lamport, mostra todos os campos dos
eventos e identifica explicitamente timestamps empatados entre agências.

## Itens ainda pendentes da Sprint 1

- Autenticação JWT.
- Frontend web.
- Funcionalidade adicional obrigatória.
- Respostas e evidências das seções restantes.
- Checklist, revisão final e merge da Sprint 1.

Nenhum desses itens é apresentado como implementado neste estágio.

## Fluxo Git atual

A branch estável `main` contém somente a estrutura inicial. O desenvolvimento das
seções 1 a 10 está na branch atual `sprint1/desenvolvimento`, com cada etapa publicada
incrementalmente. Essa branch é apresentada em um pull request draft para `main`, que
deve permanecer aberto e sem merge até a conclusão real da Sprint 1.
