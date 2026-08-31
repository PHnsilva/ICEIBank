# ICEIBank

Projeto acadêmico de sistema bancário distribuído desenvolvido em Python com FastAPI.

> Estado atual: implementação incremental da Sprint 1 na branch `sprint1/desenvolvimento`, limitada às seções 1 a 10.

O particionamento usa a regra `id_conta % 3`. As agências 0, 1 e 2 usam,
respectivamente, as portas 4078, 4079 e 4080, definidas pelo deslocamento pessoal 78.

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

Os valores monetários usam `Decimal` internamente e são devolvidos com duas casas decimais.
