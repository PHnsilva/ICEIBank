# ICEIBank

Sistema bancário distribuído acadêmico em Python/FastAPI. Sprint 1 na branch
`sprint1/desenvolvimento`: seções 1–12, frontend, JWT e histórico por conta.
O vídeo de apresentação está fora desta entrega. O PR não deve ser mesclado em `main`.

O particionamento continua `id_conta % 3`; o deslocamento pessoal 78 define:

| Agência | Porta | Frontend/API | Contas de exemplo |
| ---: | ---: | --- | --- |
| 0 | 4078 | http://localhost:4078 | 0, 3 |
| 1 | 4079 | http://localhost:4079 | 1, 4 |
| 2 | 4080 | http://localhost:4080 | 2, 5 |

## Preparação no Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/configurar_demo.py
```

A última etapa cria `.env` com duas chaves aleatórias distintas e senha Argon2id.
Ela recusa sobrescrever um arquivo existente. O login **acadêmico local** é
`aluno` / `iceibank-sprint1`. Nunca reutilize essa senha em outro ambiente.
As três instâncias leem o mesmo `.env`; `.env.example` documenta as variáveis.
Para somente executar o sistema, basta instalar `agencia/requirements.txt`.

## Execução das três agências

Abra três terminais na raiz do projeto, com o ambiente virtual ativado, e execute
um comando em cada terminal:

```powershell
$env:AGENCIA_ID="0"; python agencia/executar.py
$env:AGENCIA_ID="1"; python agencia/executar.py
$env:AGENCIA_ID="2"; python agencia/executar.py
```

Abra http://localhost:4078 e faça login. Selecione a agência; use **Abrir conta de
demonstração** para criar as contas 0 e 3 na agência 0, conta 1 na agência 1 e conta
2 na agência 2. Nenhuma conta é pré-criada em execução normal.

Consulte a conta de origem, escolha depósito, saque ou o tipo de transferência e
confirme o valor. A agência de destino é determinada pelo número da conta. Consulte
**Histórico de transações** para ver os eventos; use **Carregar mais** para páginas
adicionais. Erros HTTP e de rede aparecem na própria tela. Trocar agência limpa a
conta selecionada; sair, expirar ou recarregar a página exige novo login.

As contas e seu histórico consultável ficam somente em memória. Reiniciar apaga
esse estado; os logs JSONL em `agencia/data` permanecem para análise da linha do tempo.

## API e autenticação

A documentação interativa está em `/docs`; o contrato OpenAPI está em `/openapi.json`.
O frontend e `/config` são públicos. As rotas bancárias exigem Bearer JWT.

```powershell
Get-Date
$base = "http://localhost:4078"
$login = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" -Body '{"usuario":"aluno","senha":"iceibank-sprint1"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod "$base/contas" -Method Post -Headers $headers -ContentType "application/json" -Body '{"id":0,"nomeAluno":"Ana","saldoInicial":"100.00"}'
Invoke-RestMethod "$base/contas/0" -Headers $headers
Invoke-RestMethod "$base/contas/0/historico" -Headers $headers | ConvertTo-Json -Depth 8
```

| Método e rota | Corpo / resultado |
| --- | --- |
| `POST /auth/login` | `{"usuario":"aluno","senha":"..."}` → `access_token`, `token_type`, `expires_in` |
| `POST /contas` | `{"id":0,"nomeAluno":"Ana","saldoInicial":"100.00"}` |
| `GET /contas/{id}` | `id`, `nomeAluno`, `saldo` |
| `POST /contas/{id}/depositar` | `{"valor":"25.00"}` |
| `POST /contas/{id}/sacar` | `{"valor":"10.00"}` |
| `POST /transferencias` | `{"idOrigem":0,"idDestino":1,"valor":"30.00"}` |
| `GET /contas/{id}/historico?offset=0&limite=50` | `idConta`, `saldoAtual`, `eventos`, `total`, `offset`, `limite` |
| `POST /contas/{id}/creditar-remoto` | Exclusivo das agências; JWT de serviço vinculado ao corpo e destino |

Dinheiro usa `Decimal` no backend e strings com duas casas nas respostas.
Histórico: ordem cronológica de registro do processo atual; limite 1–100,
offset ≥ 0; cada evento contém `agencia`, `tipo`, `timestampLamport`, `horaParede`
UTC e `detalhes`. Débitos e créditos são atribuídos à conta afetada, sem incluir
movimentações de outras contas.

Códigos relevantes: **400** agência incorreta/saldo insuficiente; **401** token
faltante, inválido ou expirado/login inválido; **404** conta ausente; **409** conta
duplicada; **422** dados inválidos; **502** transferência remota não confirmada.
401 inclui `WWW-Authenticate: Bearer` e ocorre antes de alterar saldo ou Lamport.

Tokens de usuário duram 900 segundos por padrão. `JWT_TTL_SECONDS` aceita 1–86400.
Tokens entre agências duram 30 segundos e usam chave separada, origem, audiência do
destino e hash do caminho/corpo. A senha e as chaves nunca são enviadas ao frontend.
O operador acadêmico tem acesso a todas as contas; não há controle de propriedade
por cliente. HTTP é restrito a loopback; uma implantação em rede exigiria HTTPS/TLS.
JWT assina, não criptografa, e não implementa revogação/replay/idempotência nesta etapa.

## Limitação conhecida das transferências remotas

A origem é debitada antes do contato HTTP com o destino. Se a agência remota estiver
indisponível ou rejeitar o crédito, a API devolve HTTP 502 e registra
`TRANSFERENCIA_FALHOU`, mas não restaura o débito. A inconsistência é intencional
nesta Sprint e será tratada na Sprint 4. Não há 2PC, Saga, repetição automática,
compensação remota nem idempotência. A tela mostra esse erro e atualiza o saldo;
consulte a conta antes de repetir uma operação cujo resultado ficou incerto.

## Linha do tempo unificada

Depois de executar operações, rode na pasta `agencia`:

```powershell
Get-Date
python mesclar_logs.py
```

O script ordena por timestamp Lamport, mostra todos os campos e marca empates entre
agências. `horaParede` é somente critério secundário de apresentação e não prova
causalidade. As respostas das seções 6.4, 8.3 e 10 foram preservadas em [RESPOSTAS.md](RESPOSTAS.md).

## Testes e evidências reproduzíveis

Encerre as agências manuais antes dos testes de navegador: a suíte recusa portas
ocupadas e inicia seus próprios três processos nas portas oficiais, com chaves
aleatórias e dados temporários. Ela encerra somente os processos que criou.

```powershell
Get-Date
python -m pytest agencia/tests tests/e2e -q
```

Para também salvar a verificação com `Get-Date`, execute
`./scripts/verificar_sprint1.ps1`. O relatório fica em
`evidencias/sprint1/verificacao.txt`, e o teste do ciclo completo salva os saldos e
históricos reais em `evidencias/sprint1/fluxo-tres-agencias.json`.

Os testes de backend verificam regras monetárias, particionamento, logs, Lamport,
JWT e histórico. Os testes Playwright executam no Chromium real e conferem saldos
nas três APIs, erros, logout, sessão expirada, layout móvel e histórico.
As capturas são produzidas apenas depois das asserções correspondentes passarem.
Os testes de Swagger usam os assets oficiais de documentação servidos via CDN;
requerem acesso à internet. O frontend bancário não depende desses assets.

- [Checklist da Sprint](CHECKLIST_SPRINT1.md)
- [Respostas e justificativas](RESPOSTAS.md)
- [Índice e método das evidências](evidencias/sprint1/README.md)

## Fluxo Git

Commits separados para autenticação, frontend, histórico, evidências/documentação e
correções finais na branch `sprint1/desenvolvimento`. O PR existente para `main`
permanece em draft enquanto o vídeo estiver pendente, pois a condição solicitada
para marcar pronto é a conclusão integral da Sprint. O vídeo está fora deste
trabalho. Não há merge em `main`.
