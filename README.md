# ICEIBank

Sistema bancário distribuído acadêmico em **Python/FastAPI**, com frontend web,
três agências e cliente **Flutter**. Este guia explica como instalar, executar e
apresentar cada sprint separadamente no Linux. Os comandos Bash abaixo são para
Debian/Ubuntu; a seção final traz as diferenças para Windows/PowerShell.

## 1. O que apresentar em cada sprint

| Sprint | Implementação | Demonstração | Versão a executar |
| --- | --- | --- | --- |
| 1 | REST/MVC, particionamento, Lamport, JWT, frontend e histórico | Operações bancárias, transferência HTTP, falha remota e linha do tempo Lamport | Commit `21cfea62f23c6035d418556eb10fc3a6cde4bb25` |
| 2 | RabbitMQ, relógio vetorial e DLQ | Crédito assíncrono, destino desligado, concorrência/causalidade e mensagens rejeitadas | Commit `0d03c61cd96c17722eba6111cd0be8eca52ce938` |
| 3 | Bully, cliente Flutter, cache e fila offline | Eleição, falha/retorno da líder, sincronização e conflito HTTP 409 | `main` atual |
| 4 | Containers e transações distribuídas, conforme visão do roteiro | Ainda não implementada; não há demonstração de 2PC/Saga neste repositório | — |

A branch principal se chama **`main`**, não `master`. As sprints evoluem o mesmo
sistema. A versão atual **não demonstra a transferência REST nem o Lamport da
Sprint 1**. Use as versões isoladas da seção 5 para mostrar o comportamento original.
A branch `sprint3/desenvolvimento` é anterior a correções posteriores; para a
Sprint 3 use `main`.

O enunciado completo disponível é o [roteiro da Sprint 2](docs/Roteiro_Projeto_Sprint2_ICEIBank.md).
Para a Sprint 1, o escopo vem do [checklist](CHECKLIST_SPRINT1.md); o enunciado
original não está versionado. Para a Sprint 3, use o [guia](docs/Sprint3.md),
[respostas](RESPOSTAS.md#sprint-3) e [evidências](evidencias/sprint3/README.md).
Assim, este guia cobre o escopo registrado; não pressupõe requisitos de enunciados ausentes.

## 2. Instalação no Linux

### 2.1 Ferramentas e código

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip curl nodejs \
  unzip xz-utils zip libglu1-mesa

git clone https://github.com/PHnsilva/ICEIBank.git
cd ICEIBank
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/configurar_demo.py
```

Use Python **3.12 ou superior**. Se `python3 --version` indicar uma versão anterior,
instale Python 3.12+ pela distribuição e crie o ambiente com esse interpretador.
A instalação do app Flutter é separada, na seção 7.

`configurar_demo.py` cria `.env` com duas chaves aleatórias diferentes, hash
Argon2id e RabbitMQ local. **Execute uma vez por cópia do projeto**: ele recusa
sobrescrever `.env`. Para uma cópia já configurada, mantenha o arquivo existente.
Login acadêmico local: **`aluno` / `iceibank-sprint1`**.

Para os testes de interface, instale o navegador e suas bibliotecas:

```bash
python -m playwright install --with-deps chromium
```

O instalador das bibliotecas pode solicitar `sudo`. O Swagger usa assets de CDN;
seus testes precisam de internet. Os testes Python do backend não precisam do navegador.

### 2.2 RabbitMQ local para as sprints 2 e 3

Escolha **uma** opção. A Sprint 1 histórica não precisa de RabbitMQ.

**Opção A — instalação nativa Debian/Ubuntu com systemd:**

```bash
sudo apt-get install -y rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo systemctl enable --now rabbitmq-server
sudo rabbitmq-diagnostics -q ping
```

**Opção B — Docker já instalado e funcionando:**

```bash
docker run -d --name rabbitmq-iceibank \
  -p 127.0.0.1:5672:5672 -p 127.0.0.1:15672:15672 \
  rabbitmq:4-management
```

Se o container já existe e está parado, use `docker start rabbitmq-iceibank`.
Espere o broker terminar de iniciar:

```bash
curl --noproxy localhost,127.0.0.1 -fsS -u guest:guest \
  http://127.0.0.1:15672/api/overview | python3 -m json.tool
```

Abra [RabbitMQ Manager](http://127.0.0.1:15672), usuário **guest**, senha **guest**.
A porta AMQP é **5672**; a de administração é **15672**. As credenciais são
somente para demonstração local. Se já existe um broker na máquina, confira a
configuração dele antes de usar essas portas.

Alternativa CloudAMQP: defina `RABBITMQ_URL` com a URL AMQPS do seu vhost em cada
terminal das agências ou no `.env`. Os cenários automáticos deste guia usam o
broker **local**, pois criam um vhost descartável pelo Manager.

## 3. Iniciar o sistema atual: três agências

Abra **três terminais**, todos na raiz `ICEIBank`. Em cada terminal ative o
ambiente virtual. Execute **somente a agência indicada** naquele terminal:

**Terminal A — Agência 0:**

```bash
source .venv/bin/activate
export RABBITMQ_URL='amqp://guest:guest@127.0.0.1:5672/'
AGENCIA_ID=0 python agencia/executar.py
```

**Terminal B — Agência 1:**

```bash
source .venv/bin/activate
export RABBITMQ_URL='amqp://guest:guest@127.0.0.1:5672/'
AGENCIA_ID=1 python agencia/executar.py
```

**Terminal C — Agência 2:**

```bash
source .venv/bin/activate
export RABBITMQ_URL='amqp://guest:guest@127.0.0.1:5672/'
AGENCIA_ID=2 python agencia/executar.py
```

Mantenha os três terminais abertos. Espere `Application startup complete`.
Use **Ctrl+C no terminal da agência** para encerrá-la; repita seu comando para
reiniciar. Não use `pkill python`: ele pode encerrar processos de outros projetos.

| Agência | Porta | Frontend | Swagger | Contas de exemplo |
| --- | --- | --- | --- | --- |
| 0 | 4078 | [Agência 0](http://localhost:4078) | [API 0](http://localhost:4078/docs) | 0 e 3 |
| 1 | 4079 | [Agência 1](http://localhost:4079) | [API 1](http://localhost:4079/docs) | 1 |
| 2 | 4080 | [Agência 2](http://localhost:4080) | [API 2](http://localhost:4080/docs) | 2 |

O offset é 78; a agência responsável é `id_conta % 3`. Nenhuma conta é pré-criada
na execução normal. Pelo frontend, faça login, selecione a agência e use
**Abrir conta de demonstração**. Também é possível usar os comandos da seção 4.
Todos os links `localhost` se referem à máquina onde as agências estão rodando.

**Estado:** contas, saldos, histórico consultável e deduplicação das operações
offline ficam em memória. Reiniciar uma agência apaga esse estado; os arquivos
JSONL ficam em `agencia/data/`. Liderança Bully não replica contas nem muda seu
particionamento. Se a Agência 2 cair, a conta 2 continua indisponível até ela voltar.

## 4. Terminal de demonstração da API

Abra um **quarto terminal** na mesma cópia do projeto, com `.venv` ativo.
Defina as funções abaixo nesse terminal. Elas servem para as três sprints:

```bash
source .venv/bin/activate

login() {
  TOKEN=$(curl --noproxy localhost,127.0.0.1 -fsS \
    -H 'Content-Type: application/json' \
    -d '{"usuario":"aluno","senha":"iceibank-sprint1"}' \
    http://localhost:4078/auth/login \
    | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
  export TOKEN
}

api() {
  local metodo="$1" porta="$2" caminho="$3"
  shift 3
  curl --noproxy localhost,127.0.0.1 -sS \
    -w '\nHTTP %{http_code}\n' -X "$metodo" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    "$@" "http://localhost:$porta$caminho"
}

login
```

O token dura 15 minutos por padrão. Se receber 401, execute `login` de novo.
Não copie o JWT para prints públicos. As funções só existem nesse terminal;
ao abrir outro, defina-as novamente.

### 4.1 Preparar quatro contas e mostrar as operações básicas

Parta de processos recém-iniciados, sem essas contas. Na conta duplicada a API
retorna **409**; não significa falha de instalação.

```bash
date -Is
api POST 4078 /contas -d '{"id":0,"nomeAluno":"Ana","saldoInicial":"100.00"}'
api POST 4078 /contas -d '{"id":3,"nomeAluno":"Bruno","saldoInicial":"100.00"}'
api POST 4079 /contas -d '{"id":1,"nomeAluno":"Carla","saldoInicial":"100.00"}'
api POST 4080 /contas -d '{"id":2,"nomeAluno":"Diego","saldoInicial":"100.00"}'
api GET 4078 /contas/0
api POST 4078 /contas/0/depositar -d '{"valor":"25.00"}'
api POST 4078 /contas/0/sacar -d '{"valor":"10.00"}'
api POST 4078 /transferencias -d '{"idOrigem":0,"idDestino":3,"valor":"15.00"}'
api GET 4078 /contas/0
api GET 4078 /contas/3
```

Resultados: criações **201**; saldo da conta 0 **100.00** e da conta 3 **115.00**
ao terminar; transferência local **200/concluida**. Mostre também no frontend.

### 4.2 JWT, validação e histórico adicional da Sprint 1

```bash
# Sem JWT: deve retornar 401, sem alterar a conta.
curl --noproxy localhost,127.0.0.1 -sS -w '\nHTTP %{http_code}\n' \
  http://localhost:4078/contas/0

# Com JWT: 200; saque acima do saldo: 400; valor negativo: 422.
api GET 4078 /contas/0
api POST 4078 /contas/0/sacar -d '{"valor":"9999.00"}'
api POST 4078 /contas/0/depositar -d '{"valor":"-1.00"}'

# Histórico da conta e paginação: 200.
api GET 4078 '/contas/0/historico?offset=0&limite=2'
api GET 4078 '/contas/0/historico?offset=2&limite=2'

# Particionamento: conta 1 enviada à agência 0 deve retornar 400.
api POST 4078 /contas -d '{"id":1,"nomeAluno":"Agencia incorreta","saldoInicial":"1.00"}'
```

Para demonstrar expiração real, encerre as três agências e reinicie cada uma com
`JWT_TTL_SECONDS=5 AGENCIA_ID=<id> python agencia/executar.py`, substituindo `<id>`
por 0, 1 e 2. No quarto terminal faça `login`, espere `sleep 6` e consulte
`api GET 4078 /contas/0`: **401 por expiração**, mesmo que a conta tenha sido
perdida no reinício. Remova o prefixo de TTL ao voltar à execução normal.
JWT fica em memória no frontend; recarregar a página exige novo login.

## 5. Sprint 1 — executar e apresentar a versão original

### 5.1 Abrir uma cópia histórica isolada

Primeiro encerre as três agências atuais com Ctrl+C. Não misture versões nas
mesmas portas. Na raiz da cópia principal:

```bash
git fetch origin
git worktree add --detach ../ICEIBank-sprint1 21cfea62f23c6035d418556eb10fc3a6cde4bb25
cd ../ICEIBank-sprint1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/configurar_demo.py
```

Se a pasta já existe, entre nela em vez de repetir `git worktree add`.
A cópia histórica tem `.env` e logs próprios. Seu README antigo contém regras
de entrega históricas; a autorização de publicação atual se refere à `main`.

Abra três terminais **na pasta `ICEIBank-sprint1`**, ative `.venv` em cada um e rode:

| Terminal | Comando Bash |
| --- | --- |
| A | `AGENCIA_ID=0 python agencia/executar.py` |
| B | `AGENCIA_ID=1 python agencia/executar.py` |
| C | `AGENCIA_ID=2 python agencia/executar.py` |

RabbitMQ não participa desta versão. No quarto terminal, também nessa pasta,
defina as funções da seção 4 e execute os cenários 4.1 e 4.2.

### 5.2 Transferência HTTP entre agências

Depois da seção 4.1:

```bash
api POST 4078 /transferencias -d '{"idOrigem":0,"idDestino":1,"valor":"30.00"}'
api GET 4078 /contas/0
api GET 4079 /contas/1
```

Mostre **200**, origem **70.00**, destino **130.00**, o campo `timestampLamport`
nos logs e a chamada HTTP de crédito entre os processos. A transferência retorna
com o crédito remoto confirmado nesta versão.

### 5.3 Falha conhecida exigida na Sprint 1

Encerre **somente a Agência 1** com Ctrl+C no terminal B. No quarto terminal:

```bash
api POST 4078 /transferencias -d '{"idOrigem":0,"idDestino":1,"valor":"10.00"}'
api GET 4078 /contas/0
```

Espere **502**, saldo da origem **60.00** e evento `TRANSFERENCIA_FALHOU`.
Explique: o débito permanece; não existe compensação distribuída. Reinicie a
Agência 1 com o comando do terminal B e consulte a conta 1: **404**, pois estava
em memória. Não apresente o reinício como recuperação do saldo.

### 5.4 Lamport, frontend e entrega

```bash
date -Is
python agencia/mesclar_logs.py
```

Mostre ordenação por Lamport e empates. Empate não prova concorrência por si só;
timestamps diferentes também não provam causalidade. Para observar criações
independentes com contador 1, execute `python agencia/mesclar_logs.py` **antes**
das transferências e de qualquer reinício, logo após os quatro comandos de
criação de conta da seção 4.1 e antes de continuar suas movimentações.

No navegador, mostre login, seleção de agência, consulta, depósito, saque,
transferência local/remota, erro visível e **Histórico de transações** com
**Carregar mais**. O histórico por conta é o adicional desta sprint.

Confira [respostas](RESPOSTAS.md), [checklist](CHECKLIST_SPRINT1.md) e
[evidências da Sprint 1](evidencias/sprint1/README.md) na versão principal.
Os prints históricos não são provas de uma execução nova. O vídeo ficou fora
do escopo da entrega registrada; se for solicitado na apresentação, grave-o.

Para verificar a versão histórica: pare as agências, instale Chromium como na
seção 2.1 e rode `python -m pytest agencia/tests tests/e2e -q` nessa cópia.
Essa suíte gera capturas em `evidencias/sprint1/`; não as confunda com os registros anteriores.

## 6. Sprint 2 — RabbitMQ, vetores e resiliência

### 6.1 Abrir a versão da Sprint 2

Encerre as agências da Sprint 1. Volte à cópia principal `ICEIBank` e execute:

```bash
git worktree add --detach ../ICEIBank-sprint2 0d03c61cd96c17722eba6111cd0be8eca52ce938
cd ../ICEIBank-sprint2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/configurar_demo.py
```

Inicie RabbitMQ pela seção 2.2. Para uma demonstração manual, abra os três
terminais **nessa pasta** e use os comandos da seção 3. Nesta versão não há Bully.
Use a seção 4 para criar contas e demonstrar JWT/frontend/histórico preservados.

### 6.2 Mostrar uma transferência assíncrona manualmente

Depois de executar a seção 4.1 em processos limpos:

```bash
api POST 4078 /transferencias -d '{"idOrigem":0,"idDestino":1,"valor":"15.00"}'
api GET 4078 /contas/0
api GET 4079 /contas/1
```

A transferência retorna **200**, `status=publicada`, `vetorEnvio` e
`idTransferencia`, sem prometer saldo de destino. Consulte novamente o destino
se o consumo ainda não terminou. Resultado final: origem **85.00**, destino
**115.00**. Logs agora usam `timestampVetorial`, com três posições.
A rota REST `creditar-remoto` da Sprint 1 foi removida.

No Manager, selecione o vhost `/` e mostre:

| Item | O que conferir |
| --- | --- |
| Exchange `iceibank.eventos` | Tipo `topic`, durável |
| Filas `fila-agencia-0`, `fila-agencia-1`, `fila-agencia-2` | Duráveis, uma por agência |
| Bindings | `agencia.0.creditar`, `agencia.1.creditar`, `agencia.2.creditar` |
| Exchange `iceibank.nao-processadas` e filas com sufixo `.nao-processadas` | DLX/DLQs do adicional |

O código publica mensagem persistente, pede confirmação do broker e dá ack
manual só depois de processar. Fila durável e mensagem persistente não tornam
as contas em memória persistentes.

### 6.3 Quatro cenários automáticos, um por vez

**Encerre as três agências manuais antes.** Esses comandos iniciam seus próprios
processos nas portas oficiais. Deixe apenas RabbitMQ ligado. No quarto terminal,
na raiz `ICEIBank-sprint2`, com `.venv` ativo:

```bash
export RABBITMQ_URL_TESTES='amqp://guest:guest@127.0.0.1:5672/'
export RABBITMQ_MANAGEMENT_URL_TESTES='http://127.0.0.1:15672'
mkdir -p .local/apresentacao/sprint2

# 1. Transferência assíncrona e confirmação por consulta ao destino.
date -Is
python -m scripts.demonstrar_sprint2 transferencia --saida .local/apresentacao/sprint2

# 2. Destino desligado, fila retida, reinício e conta perdida.
date -Is
python -m scripts.demonstrar_sprint2 resiliencia --saida .local/apresentacao/sprint2

# 3. Eventos concorrentes e débito causalmente anterior ao crédito.
date -Is
python -m scripts.demonstrar_sprint2 causal --saida .local/apresentacao/sprint2

# 4. Adicional: mensagem preservada na DLQ e ausência de reaplicação automática.
date -Is
python -m scripts.demonstrar_sprint2 adicional --saida .local/apresentacao/sprint2
```

Cada comando deve terminar com **`Verificações do cenário: OK`**. Aguarde sua
conclusão antes do seguinte. Cada execução cria/remove apenas seu vhost aleatório
e seus processos; os logs e JSONs locais permanecem. As estatísticas do Manager
podem levar alguns segundos para refletir o consumo.

| Cenário | Resultado a explicar | Print exigido pelo roteiro |
| --- | --- | --- |
| `transferencia` | Origem 85.00, destino 115.00; publicada não significa creditada | `transferencia-assincrona.png` |
| `resiliencia` | 1 mensagem retida, 0 consumidores; ao reiniciar, conta 404 e crédito rejeitado | `resiliencia-fila.png` |
| `causal` | Criações independentes concorrentes; débito ANTES do crédito, nunca concorrentes entre si | `linha-do-tempo-causal.png` |
| `adicional` | `x-death.reason=rejected`; conta recriada com 1.00 continua com 1.00 | `funcionalidade-adicional.png` |

Capture o terminal real com a data e a saída visíveis. O cenário de resiliência
**não demonstra dinheiro recuperado**: a DLQ guarda o crédito rejeitado e o saldo
da origem continua debitado. Não recrie a conta antes do consumo para esconder a perda.
Para uma nova análise causal, use os logs `execucao-causal-*` de **uma execução**:
`python agencia/mesclar_logs.py --dados <pasta-exata-da-execucao>`.
Não misture reinícios que zeram vetores.

As saídas acima vão para `.local/` para preservar as evidências já versionadas.
Para preparar uma nova entrega, revise e copie as capturas aprovadas para
`evidencias/sprint2/` com os nomes da tabela, junto dos JSONs/logs correspondentes.
Não substitua evidências históricas inadvertidamente.

Para a regressão completa, com Chromium instalado e agências manuais paradas:

```bash
python -m pytest agencia/tests tests/e2e -q
```

Os testes de navegador podem atualizar `evidencias/sprint2/regressao/`.
Confira o [checklist](CHECKLIST_SPRINT2.md), as perguntas **6.4, 7.5 e 8.3** em
[RESPOSTAS.md](RESPOSTAS.md) e a declaração de uso de IA antes de apresentar.

## 7. Sprint 3 — executar o app de celular

Encerre as agências da Sprint 2, volte à raiz da cópia principal **`ICEIBank`** e
inicie RabbitMQ e as três agências como na seção 3. Use `.env` dessa cópia.

### 7.1 Instalar Flutter no Linux

```bash
mkdir -p "$HOME/develop"
git clone --branch 3.50.1 --depth 1 https://github.com/flutter/flutter.git "$HOME/develop/flutter"
export PATH="$HOME/develop/flutter/bin:$PATH"
flutter --version
flutter doctor -v
```

A versão fixada acima é Flutter **3.50.1**, com Dart **3.14.0**.
Se Flutter já existe nesse caminho, não repita o clone. Adicione o `export PATH`
ao seu `~/.bashrc` para reutilizar em novos terminais. O `pubspec.yaml` exige
**Dart 3.13.7 ou superior compatível com a série 3**; `flutter --version` precisa
mostrar uma versão compatível. Use o [SDK oficial](https://docs.flutter.dev/install/manual)
se precisar selecionar outra versão. Só são necessários os componentes da
plataforma escolhida: avisos sobre iOS não impedem Android ou Web no Linux.

Na raiz do repositório:

```bash
cd app_mobile
flutter pub get
flutter analyze
flutter test
```

### 7.2 Android em emulador — demonstração móvel nativa

1. Instale [Android Studio](https://developer.android.com/studio) e complete o
   assistente. Em **More Actions → SDK Manager** (ou **Tools → SDK Manager**),
   instale a plataforma Android exigida pelo Flutter e, em **SDK Tools**,
   Android SDK Build-Tools, Command-line Tools, Platform-Tools e Android Emulator.
2. Execute `flutter doctor --android-licenses`, leia/aceite as licenças aplicáveis
   e confira `flutter doctor -v`. Siga os diagnósticos até o Android toolchain ficar pronto.
3. Em **Device Manager → Create Virtual Device**, escolha um celular Pixel,
   baixe uma imagem de sistema compatível com sua arquitetura e inicie o AVD.
   No Linux, verifique acesso a **`/dev/kvm`** para aceleração. Em máquina virtual,
   a virtualização aninhada precisa estar disponível no host; instalar Flutter
   sozinho não cria essa capacidade.
4. Com o emulador iniciado, na pasta `app_mobile`:

```bash
flutter emulators
flutter devices
flutter run --debug -d <ID_ANDROID_MOSTRADO_EM_FLUTTER_DEVICES>
```

Substitua o marcador pelo ID real, por exemplo `emulator-5554` **se aparecer na
lista**. O host padrão do app é `10.0.2.2`, que representa o computador dentro
do Android Emulator. Não use `localhost` como host do backend nesse caso.
Mantenha o terminal do Flutter aberto; `q` encerra a execução.

O repositório contém a plataforma Android. Se o SDK exigir os launchers Gradle
locais ausentes, execute `flutter create --platforms=android --project-name
iceibank_mobile .` nessa pasta e revise `git diff` antes de versionar os arquivos
gerados; não substitua configurações próprias de Android por outras sem revisão.

### 7.3 Android físico por USB

Ative as opções de desenvolvedor/depuração USB no aparelho e autorize o
computador. Depois, com `adb` do Android SDK no PATH:

```bash
adb devices
adb reverse tcp:4078 tcp:4078
adb reverse tcp:4079 tcp:4079
adb reverse tcp:4080 tcp:4080
flutter devices
flutter run --debug -d <ID_DO_CELULAR> --dart-define=ICEIBANK_HOST=127.0.0.1
```

O USB não fica disponível automaticamente em um ambiente remoto. `adb reverse`
pode continuar transportando requisições mesmo com Wi-Fi desligado; por isso,
modo avião nessa configuração não é prova suficiente do modo offline.

### 7.4 Alternativa sem emulador: app Flutter no navegador

O mesmo cliente Dart pode ser executado como **Flutter Web**, em tela de celular.
Isso permite mostrar o cliente, cache/fila e Bully, mas **não equivale à validação
Android nem à captura de modo avião do aparelho**. A versão principal inclui o
alvo Web e permite a origem local de desenvolvimento na porta 8080.

Na pasta `app_mobile`, com as agências da `main` ligadas:

```bash
flutter pub get
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=8080 \
  --dart-define=ICEIBANK_HOST=localhost
```

Abra [app Flutter local](http://127.0.0.1:8080) no navegador **da mesma máquina**.
Use as ferramentas do navegador para uma janela de celular, por exemplo
390 × 844. Essa janela é uma apresentação móvel do cliente Web.
Se houver erro CORS, confirme que as agências usam a `main` atual, reiniciadas
após a atualização; use exatamente a porta **8080** e um dos hosts loopback
`localhost`/`127.0.0.1`. Não desative a segurança do navegador.

## 8. Sprint 3 — roteiro de apresentação, na ordem

### 8.1 Eleição inicial, failover e retorno

Com as três agências da `main` ligadas, no quarto terminal:

```bash
date -Is
for porta in 4078 4079 4080; do
  curl --noproxy localhost,127.0.0.1 -fsS "http://localhost:$porta/bully/lider"
  printf '\n'
done
```

Espere as três respostas convergirem para **`liderAtual: 2`**. No app, observe o
painel de liderança. Encerre **somente a Agência 2** com Ctrl+C no terminal C.
Após alguns segundos, repita as consultas **apenas às portas 4078 e 4079**:
as duas devem informar **líder 1**, e o app deve atualizar sem recarregamento manual.
Reinicie a Agência 2 no terminal C e repita o laço completo: volta a **líder 2**.

Bully prefere o maior ID acessível. Pode haver líderes transitórias durante a
subida/partição; não apresente isso como consenso forte ou replicação financeira.
Ao parar uma agência, suas contas em memória são perdidas.

### 8.2 Histórico de liderança

```bash
date -Is
node agencia/historico-lideranca.js
```

Mostre declarações da eleição inicial, da falha e do retorno. Para uma sessão
isolada, copie **os JSONL de liderança dessa sessão** para uma pasta própria e
use `node agencia/historico-lideranca.js --dados <pasta>`.
Esse histórico é por hora de parede; não é a análise de concorrência vetorial.

### 8.3 Operação offline e sincronização sem conflito

1. No app faça login com `aluno` / `iceibank-sprint1`.
2. Crie a conta **0 com 100.00**, se ainda não existir, e execute **Consultar saldo**.
   Ela pertence à Agência 0, que não foi encerrada no cenário de failover.
   Se usar uma conta existente, anote o saldo confirmado como **S**.
3. Isole **a rede do cliente**, mantendo os servidores ligados. No Android
   Emulator, ative modo avião e confirme que o painel perdeu acesso às agências.
   Na versão Web, use **DevTools → Network → Offline**, mantendo a página carregada.
4. Selecione **Depositar**, conta 0, valor **20.00**, e envie. Mostre saldo
   provisório **S + 20.00** e uma operação pendente no armazenamento local.
5. Restaure a rede/Network → Online com o app aberto em primeiro plano.
   Não faça outra movimentação no backend enquanto demonstra o caminho sem conflito.
6. Aguarde sincronizar: o saldo confirmado passa a **S + 20.00** e a fila fica vazia.
   Consulte também a conta pela API para confirmar que o depósito chegou.

O cache precisa de uma consulta online inicial. Login e transferências exigem
rede. O JWT fica em memória; fechar o app exige login online novamente para
retomar a fila. Não apague o armazenamento do app durante a demonstração.

### 8.4 Conflito offline: rejeitar, mostrar saldo atual e revisar

1. Com o app online, consulte a conta 0 novamente; guarde o saldo confirmado **S**.
2. Coloque **só o cliente** offline e registre um **saque de 10.00** nessa conta.
3. No quarto terminal da raiz, com as funções da seção 4 e token válido:

```bash
login
api POST 4078 /contas/0/depositar -d '{"valor":"5.00"}'
```

4. Reconecte o cliente. O vetor conhecido ficou desatualizado: o backend retorna
   **409**, não aplica o saque e devolve a conta atualizada.
5. Mostre a operação rejeitada, a retirada da projeção provisória e o saldo
   confirmado **S + 5.00**. Revise a pendência e, se quiser reaplicá-la, use **Dispensar avisos desta conta**
   e envie uma **nova operação** após consultar o estado atual.

Os vetores são da **agência**, não exclusivos de cada conta. Mensagens Bully e
outras operações nessa agência também podem avançá-los. Se o cenário sem
conflito receber 409, mostre o comportamento real; não altere relógios para
forçar uma confirmação. O cliente também envia `versaoAgencia` para detectar
reinícios e `operacaoId` para não reaplicar a mesma sincronização no processo atual.

### 8.5 Mostrar o 409 diretamente na API

Com a conta 0 existente e as funções da seção 4 definidas, salve o vetor e depois
altere a conta antes de tentar sincronizar:

```bash
login
mkdir -p .local/apresentacao/sprint3
curl --noproxy localhost,127.0.0.1 -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:4078/contas/0 > .local/apresentacao/sprint3/conta-antes.json
api POST 4078 /contas/0/depositar -d '{"valor":"5.00"}'
python - <<'PY'
import json
from pathlib import Path
from uuid import uuid4
pasta = Path('.local/apresentacao/sprint3')
conta = json.loads((pasta / 'conta-antes.json').read_text())
pedido = {'tipo': 'SAQUE', 'valor': '10.00',
          'vetorConhecido': conta['vetorAtual'],
          'versaoAgencia': conta['versaoAgencia'], 'operacaoId': str(uuid4())}
(pasta / 'pedido-conflito.json').write_text(json.dumps(pedido))
PY
date -Is
api POST 4078 /contas/0/sincronizar \
  --data-binary @.local/apresentacao/sprint3/pedido-conflito.json
api GET 4078 /contas/0
```

Mostre **409**, `vetorConhecido`, `vetorAtual`, `relacao` e `contaAtual`.
O saque não deve aparecer como aplicado no saldo/histórico.

### 8.6 Funcionalidade adicional: ajustar os tempos do Bully

Encerre a agência desejada e reinicie no terminal correspondente; exemplo da 2:

```bash
BULLY_HEARTBEAT_SEGUNDOS=1.5 BULLY_TIMEOUT_SEGUNDOS=0.5 \
  AGENCIA_ID=2 python agencia/executar.py
```

Mostre no log a configuração aplicada. Para ajustar a velocidade de detecção
das seguidoras, configure **também as Agências 0 e 1**, cada uma com seu ID.
Padrões: heartbeat **3 s**, timeout HTTP **1 s**. Valores precisam ser positivos,
com ponto decimal. Repetir o ensaio de falha permite observar a diferença;
não prometa um prazo exato de eleição, que depende dos timeouts e da rede.

### 8.7 Capturas e verificação

| Captura | Mostrar |
| --- | --- |
| `eleicao-inicial.png` | Três respostas com líder 2 |
| `failover.png` | Remanescentes com líder 1 |
| `historico-lideranca.png` | Eleição inicial, falha e retorno |
| `app-lider-atual.png` / `app-failover.png` | Painel do cliente antes/depois |
| `app-offline.png` / `app-sincronizacao.png` | Pendência/saldo provisório e confirmação/fila vazia |
| `conflito-sincronizacao.png` / `app-conflito.png` | 409 na API e revisão no cliente |
| `funcionalidade-adicional.png` | Configuração dos tempos no log |

Registre data real, plataforma usada e limitações. A evidência histórica da
Sprint 3 foi produzida em Flutter Web; a validação Android ficou pendente naquele
ambiente. Não renomeie uma captura Web como se fosse Android.

Para conferir automaticamente: pare as três agências manuais, mantenha RabbitMQ,
defina as duas variáveis de testes da seção 6.3 e, **na raiz da `main`**, execute:

```bash
python -m pytest agencia/tests -q
python -m pytest tests/e2e/test_sprint2.py tests/e2e/test_sprint3.py -q
# Com Chromium e acesso à CDN do Swagger:
python -m pytest agencia/tests tests/e2e -q
cd app_mobile
flutter analyze
flutter test
```

Não some resultados de execuções históricas como se fossem uma nova validação.
O teste `test_sprint3.py` demonstra eleição/failover por API; os testes Flutter
cobrem lógica do cliente. Eles não substituem o ensaio visual do app em Android.

## 9. Contrato, segurança e limitações para explicar

| Método e rota | Finalidade |
| --- | --- |
| `POST /auth/login` | Emitir JWT de operador |
| `POST /contas` | Criar (`id`, `nomeAluno`, `saldoInicial`) |
| `GET /contas/{id}` | Saldo; na Sprint 3 também vetor e versão da agência |
| `POST /contas/{id}/depositar` / `/sacar` | Movimentar `valor` positivo |
| `POST /transferencias` | Transferir (`idOrigem`, `idDestino`, `valor`) |
| `GET /contas/{id}/historico?offset=0&limite=50` | Histórico autenticado; limite 1–100 |
| `GET /bully/lider` | Líder percebida, público na Sprint 3 |
| `POST /bully/eleicao` / `/bully/coordenador` | Mensagens entre agências, JWT interno |
| `POST /contas/{id}/sincronizar` | Operação offline, validação do vetor e 409 na Sprint 3 |

Dinheiro usa `Decimal` e respostas com duas casas. JWT assina, não criptografa;
operador acadêmico pode acessar todas as contas. Login, frontend e `/config`
são públicos; operações bancárias exigem Bearer JWT. Chaves de operador e de
agências são distintas; o crédito AMQP confia nas credenciais/permissões do broker,
não em JWT HTTP. Em AMQPS a validação TLS permanece habilitada.

Transferência local restaura o débito se o destino local não existe. Transferência
remota nas sprints 2/3 apenas confirma publicação. Falha de publicação retorna
**502 com débito mantido**, e o resultado pode ser incerto. Não há Saga/2PC,
persistência das contas nem idempotência geral de transferências remotas.
`idTransferencia` correlaciona eventos, não garante execução única.
A deduplicação de `operacaoId` limita-se à sincronização offline e à memória
da instância. DLQ não compensa a origem e não reprocessa automaticamente.

## 10. Problemas comuns

| Sintoma | Ação |
| --- | --- |
| `python`/dependência ausente | Ative `.venv` da cópia correta e instale `requirements-dev.txt` |
| `.env` já existe | Não repita o gerador; mantenha a configuração local existente |
| Falha AMQP na subida | Confira broker, porta 5672 e `RABBITMQ_URL` em cada terminal |
| Porta 4078/4079/4080 ocupada | Pare a agência anterior; não execute duas sprints ao mesmo tempo |
| Conta 404 depois de reiniciar | Recrie apenas para um novo cenário; contas não são persistidas |
| Login/consulta 401 | Faça login novamente; confira as mesmas chaves entre as agências |
| Agências inacessíveis no Android | Use `10.0.2.2` no AVD ou USB + `adb reverse` e host 127.0.0.1 |
| Sem emulador ou sem `/dev/kvm` | Configure virtualização no host, use aparelho USB ou demonstre Flutter Web |
| Flutter Web sem acesso/CORS | Use a `main` atual e origem local porta 8080; reinicie as agências |
| `PRECONDITION_FAILED` em filas | Filas antigas sem DLX: use novo vhost de demonstração; não apague filas com dados para contornar |
| Falha de proxy SOCKS em chamadas locais | Em um terminal dedicado ao ensaio local, remova variáveis de proxy como abaixo |
| Falha ao instalar Chromium/SDK | Confira acesso aos servidores oficiais; registre a limitação sem declarar testes visuais aprovados |

Se o ambiente injeta proxies, para executar apenas serviços e ensaios locais:

```bash
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export NO_PROXY=localhost,127.0.0.1
```

Isso vale só para esse terminal. Instalações que precisam da rede corporativa
podem depender do proxy; mantenha um terminal separado para elas.

## 11. Windows/PowerShell

Na raiz da cópia escolhida:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/configurar_demo.py
```

RabbitMQ portátil Windows: `./scripts/iniciar_rabbitmq_local.ps1`, mantido em um
terminal próprio, ou use Docker. O script baixa distribuições oficiais para
`.local/`, sem instalar serviço nem mudar PATH global. Não execute o script `.ps1`
no Bash do Linux.

Em **três terminais** com `.venv` ativo, defina `RABBITMQ_URL` nas sprints 2/3 e
rode um ID por terminal:

```powershell
$env:RABBITMQ_URL = 'amqp://guest:guest@127.0.0.1:5672/'
$env:AGENCIA_ID = '0'; python agencia/executar.py
# Outro terminal: AGENCIA_ID = '1'. Outro: AGENCIA_ID = '2'.
```

Para os cenários automáticos da Sprint 2, pare as agências manuais e execute:

```powershell
$env:RABBITMQ_URL_TESTES = 'amqp://guest:guest@127.0.0.1:5672/'
$env:RABBITMQ_MANAGEMENT_URL_TESTES = 'http://127.0.0.1:15672'
Get-Date -Format o
python -m scripts.demonstrar_sprint2 transferencia --saida .local/apresentacao/sprint2
python -m scripts.demonstrar_sprint2 resiliencia --saida .local/apresentacao/sprint2
python -m scripts.demonstrar_sprint2 causal --saida .local/apresentacao/sprint2
python -m scripts.demonstrar_sprint2 adicional --saida .local/apresentacao/sprint2
```

Os comandos `flutter` da seção 7 são os mesmos; escreva-os em uma linha no
PowerShell em vez de usar `\` para continuação. Para heartbeat use
`$env:BULLY_HEARTBEAT_SEGUNDOS='1.5'`; para timeout,
`$env:BULLY_TIMEOUT_SEGUNDOS='0.5'`. Use `Get-Date -Format o` nas capturas Windows.
Os exemplos de API com funções Bash exigem Bash; no PowerShell use o Swagger
ou o frontend para as mesmas entradas e resultados descritos.

## 12. Documentação e evidências

- [Roteiro original da Sprint 2](docs/Roteiro_Projeto_Sprint2_ICEIBank.md)
- [Checklist Sprint 1](CHECKLIST_SPRINT1.md) e [Checklist Sprint 2](CHECKLIST_SPRINT2.md)
- [Guia Sprint 3](docs/Sprint3.md) e [guia Android](app_mobile/README.md)
- [Respostas, justificativas e uso de IA](RESPOSTAS.md)
- [Evidências Sprint 1](evidencias/sprint1/README.md), [Sprint 2](evidencias/sprint2/README.md) e [Sprint 3](evidencias/sprint3/README.md)

Codex (OpenAI) apoiou implementação, testes e documentação. O autor deve revisar
e conseguir explicar o código e as respostas. Os exemplos Node.js do roteiro
foram adaptados para Python conforme a seção 9 do enunciado. Commits e evidências
registram trabalho real; não altere datas para simular execução anterior.
