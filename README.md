# ICEIBank

Sistema bancário distribuído acadêmico em **Python/FastAPI**. A Sprint 2 evolui a
Sprint 1 no mesmo repositório: substitui Lamport por relógio vetorial e crédito
remoto REST por Publish/Subscribe com RabbitMQ. JWT, frontend, particionamento e
histórico por conta continuam funcionando. Contas e saldos continuam em memória.

O [PR #1](https://github.com/PHnsilva/ICEIBank/pull/1) da Sprint 1 foi integrado à
`main`; suas evidências permanecem em `evidencias/sprint1/`. A evolução está na
branch `sprint2/desenvolvimento`, sem merge automático. O vídeo da entrega
anterior era uma pendência fora do escopo; não se afirma sua entrega externa.

Referência: [roteiro da Sprint 2](docs/Roteiro_Projeto_Sprint2_ICEIBank.md).
Os exemplos Node.js foram adaptados para Python, conforme a seção 9.

## Preparação no Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/configurar_demo.py
```

O gerador cria `.env` com chaves distintas, senha Argon2id e URL do RabbitMQ local;
recusa sobrescrever configuração existente. Login acadêmico local:
`aluno` / `iceibank-sprint1`. Não versione `.env` nem a URL com credenciais reais.

## RabbitMQ: CloudAMQP ou alternativa local

Para CloudAMQP, crie a instância conforme a seção 4.1 do roteiro e use sua URL
AMQPS em cada terminal das agências, ou no `.env` local:

```powershell
$env:RABBITMQ_URL = "amqps://usuario:senha@host.cloudamqp.com/vhost"
```

Sem URL válida a aplicação recusa iniciar. O painel CloudAMQP oferece RabbitMQ
Manager. Esta entrega foi validada com RabbitMQ **local real**, alternativa
permitida pelo roteiro; não se afirma criação ou validação de uma conta CloudAMQP.

Para RabbitMQ local portátil, abra um terminal e mantenha-o em execução:

```powershell
./scripts/iniciar_rabbitmq_local.ps1
```

O script baixa distribuições oficiais RabbitMQ 4.3.6/Erlang 28.3 para `.local/`
(ignoradas pelo Git), sem instalar serviço ou mudar o PATH global. O broker e
a administração escutam somente em loopback. Manager:
http://127.0.0.1:15672, login acadêmico local `guest` / `guest`.

Também é possível usar a alternativa Docker do roteiro, vinculada ao loopback:

```powershell
docker run -d --name rabbitmq-iceibank -p 127.0.0.1:5672:5672 -p 127.0.0.1:15672:15672 rabbitmq:3-management
```

Execute somente uma alternativa nas mesmas portas. A aplicação declara a
exchange topic durável `iceibank.eventos`, três filas duráveis
`fila-agencia-0/1/2` e bindings `agencia.<id>.creditar`. Todas as filas são
declaradas antes de publicar, inclusive se uma agência nunca iniciou.

## Execução das três agências

O offset pessoal 78 é preservado; a agência de uma conta é `id_conta % 3`.
Em três terminais na raiz, com o ambiente virtual ativado:

```powershell
$env:RABBITMQ_URL="amqp://guest:guest@127.0.0.1:5672/"
$env:AGENCIA_ID="0"; python agencia/executar.py # porta 4078
$env:AGENCIA_ID="1"; python agencia/executar.py # porta 4079, em outro terminal
$env:AGENCIA_ID="2"; python agencia/executar.py # porta 4080, em outro terminal
```

Abra http://localhost:4078, faça login e selecione a agência. Crie as contas de
demonstração antes de movimentar: 0 e 3 na Agência 0, 1 na Agência 1, 2 na Agência 2.
O frontend oferece criação, saldo, depósito, saque, transferência local/remota e
histórico paginado. Troca de agência limpa a seleção; expiração/401 limpa a sessão.
O JWT fica apenas em memória no navegador; erros da API aparecem na interface.

## Contrato e comportamento das transferências

As rotas bancárias exigem Bearer JWT. Login, frontend e `/config` são públicos;
Swagger está em `/docs`. Dinheiro usa Decimal e strings com duas casas decimais.

| Método e rota | Finalidade |
| --- | --- |
| `POST /auth/login` | Emitir JWT a partir de usuário/senha |
| `POST /contas` | Criar conta (`id`, `nomeAluno`, `saldoInicial`) |
| `GET /contas/{id}` | Consultar saldo |
| `POST /contas/{id}/depositar` ou `/sacar` | Movimentar `valor` positivo |
| `POST /transferencias` | Transferir (`idOrigem`, `idDestino`, `valor`) |
| `GET /contas/{id}/historico?offset=0&limite=50` | Histórico por conta; limite 1–100 |

**Local:** débito e crédito no mesmo processo; HTTP 200, `status=concluida` e
saldos confirmados. Destino local inexistente retorna 404 e registra estorno.

**Remota:** débito na origem, incremento do envio e publicação de mensagem
persistente na routing key do destino. O broker confirma a publicação; HTTP 200
retorna `status=publicada`, `vetorEnvio` e `idTransferencia`, sem `saldoDestino`.
Isso não confirma o crédito. A interface orienta consultar o destino depois.
O consumidor combina o vetor recebido e aplica o crédito antes de ack manual.
A rota `/contas/{id}/creditar-remoto` foi removida.

O crédito pelo broker não carrega JWT HTTP. A confiança é nas credenciais,
vhost e permissões AMQP; o consumidor valida mensagem, valores, origem e partição.
Tokens de serviço HTTP da Sprint 1 ficaram apenas como código de consulta; não
são utilizados no consumidor. AMQPS mantém a validação TLS padrão do cliente.

**Limitações do roteiro:** reiniciar uma agência apaga contas e histórico em
memória. A mensagem retida chega, mas pode encontrar a conta ausente. A DLQ
preserva o crédito rejeitado; não restaura o saldo da origem. Falha de publicação
retorna 502 com débito mantido e resultado possivelmente incerto. Não há
persistência de contas, compensação distribuída ou garantia de execução única.
O identificador correlaciona os eventos; não implementa idempotência.

## Relógio vetorial e linha do tempo

O relógio tem três posições: local/envio incrementam a posição própria;
recebimento mescla pelo máximo e incrementa a posição local. Logs JSONL em
`agencia/data/` usam `timestampVetorial`, agência, tipo, hora UTC e detalhes.
O registrador copia snapshots para evitar alterar timestamps já registrados.

```powershell
Get-Date
python agencia/mesclar_logs.py
# Ou analisar somente uma execução, sem misturar processos reiniciados:
python agencia/mesclar_logs.py --dados caminho/dos/logs/desta-execucao
```

Hora de parede ordena a apresentação; a comparação vetorial determina causalidade
e identifica pares concorrentes entre agências diferentes. Logs Lamport antigos
permanecem no disco e são excluídos da análise com aviso. Vetores pressupõem
identidades/contadores contínuos: use logs de uma execução para comparar causalidade,
sem misturar reinícios que zeram o relógio. O script não inventa concorrência
a partir de empates Lamport e recusa regressão/repetição do contador local,
evitando tratar reinícios detectados como uma execução contínua.

## Funcionalidade adicional da Sprint 2

Dead-letter exchange topic durável `iceibank.nao-processadas`, com uma DLQ
`fila-agencia-<id>.nao-processadas` por agência. Falha de crédito rejeita e
reenfileira na primeira entrega; falha na redelivery rejeita sem requeue e segue
à DLQ. Erro interno inesperado segue diretamente à DLQ. A mensagem fica disponível
no Manager com `x-death`, sem reprocessamento automático. Detalhes e respostas
conceituais estão na seção Sprint 2 de [RESPOSTAS.md](RESPOSTAS.md).

Filas preexistentes sem a configuração DLX não aceitam mudança de argumentos:
use um vhost novo para esta sprint ou migre filas vazias conscientemente no
Manager. A aplicação não apaga filas ou mensagens para contornar incompatibilidade.

## Testes, resiliência e evidências reais

Encerre as agências manuais antes dos testes: a suíte recusa portas ocupadas.
Para o broker local, defina:

```powershell
$env:RABBITMQ_URL_TESTES="amqp://guest:guest@127.0.0.1:5672/"
$env:RABBITMQ_MANAGEMENT_URL_TESTES="http://127.0.0.1:15672"
./scripts/verificar_sprint2.ps1
```

O ambiente cria um vhost aleatório exclusivo, usa chaves e contas de teste, inicia
três agências reais e remove somente o vhost/processos criados por ele. Também
aceita `RABBITMQ_URL_TESTES` apontando a um vhost exclusivo previamente criado;
sem Management URL, as inspeções do Manager não são realizadas, embora a
integração AMQP continue real. A verificação registrada desta entrega inclui
Manager, durabilidade, bindings e DLQ. A URL de testes nunca deve apontar a filas
de trabalho ou contas reais. Credenciais não são exibidas nos relatórios.

```powershell
./scripts/demonstrar_sprint2.ps1 transferencia
./scripts/demonstrar_sprint2.ps1 resiliencia
./scripts/demonstrar_sprint2.ps1 causal
./scripts/demonstrar_sprint2.ps1 adicional
```

Cada demonstração gera logs, resultados JSON e saída de terminal reais em
`evidencias/sprint2/`, com Get-Date. Capture a tela do terminal após a execução.
O cenário de resiliência termina/reinicia o processo de destino, sem restaurar
contas. O cenário causal comprova criações concorrentes e débito anterior ao crédito.
As capturas da regressão são produzidas pelo Chromium após as asserções e ficam
em `evidencias/sprint2/regressao/`; os PNGs da Sprint 1 são preservados.

- [Checklist Sprint 2](CHECKLIST_SPRINT2.md)
- [Evidências Sprint 2](evidencias/sprint2/README.md)
- [Checklist histórico Sprint 1](CHECKLIST_SPRINT1.md)
- [Evidências históricas Sprint 1](evidencias/sprint1/README.md)

## Uso de IA e referências

Codex (OpenAI) apoiou implementação, testes e documentação. A declaração está em
`RESPOSTAS.md`; o autor precisa revisar e conseguir explicar a entrega.
Commits incrementais separam relógio, mensageria, causalidade, funcionalidade
adicional, documentação e evidências, com datas reais do trabalho.

Referências: [aio-pika](https://docs.aio-pika.com/quick-start.html),
[confirmações RabbitMQ](https://www.rabbitmq.com/docs/confirms),
[DLX](https://www.rabbitmq.com/docs/dlx),
[compatibilidade Erlang/RabbitMQ](https://www.rabbitmq.com/docs/which-erlang).
