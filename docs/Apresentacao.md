# Apresentação das três sprints

A demonstração executa cada versão em processos reais, usa RabbitMQ nas sprints 2 e 3 e apresenta o cliente Flutter em uma tela de celular. O vídeo é um MP4 1920 × 1080, sem faixa de áudio, com capturas lentas, legendas incorporadas e trechos reais do código ao lado das operações.

## Preparar

Use Linux, Python 3.12+, Git, Flutter 3.50.1, FFmpeg e as fontes DejaVu. Instale e inicie RabbitMQ com o plugin `rabbitmq_management`, conforme o README. O broker precisa aceitar a criação de vhosts descartáveis para a demonstração. Os padrões locais são AMQP em `127.0.0.1:5672` e Manager em `127.0.0.1:15672`, usuário/senha `guest`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m scripts.preparar_apresentacao --flutter /caminho/flutter/bin/flutter
python -m playwright install chromium
```

O preparador instala `requirements-demo.txt`, cria duas worktrees em `.local/sprints/` e compila o Flutter Web para usar `127.0.0.1` como host das agências. Os recursos do renderizador Web são incluídos no build, sem depender de CDN durante a demonstração. O modo automatizado do SDK (`BOT=true`, `CI=true`) desativa sua sondagem de metadados de infraestrutura.

| Sprint | Código executado | Transporte e relógio |
| --- | --- | --- |
| 1 | `21cfea62f23c6035d418556eb10fc3a6cde4bb25` | Crédito remoto HTTP; Lamport |
| 2 | `0d03c61cd96c17722eba6111cd0be8eca52ce938` | RabbitMQ; vetores |
| 3 | Checkout atual | RabbitMQ; vetores; Bully; Flutter offline |

## Rodar para apresentar ao vivo

Escolha uma sprint por vez:

```bash
python -m scripts.iniciar_apresentacao 1
# Ctrl+C antes de iniciar outra versão.
python -m scripts.iniciar_apresentacao 2
# Ctrl+C antes de iniciar outra versão.
python -m scripts.iniciar_apresentacao 3
```

O comando inicia as três agências, cria contas 0, 1, 2 e 3 com R$ 100,00 e mantém os processos ativos até Ctrl+C. A web fica em `http://localhost:4078`; as outras agências usam 4079 e 4080. Na Sprint 3, o cliente Flutter fica em `http://127.0.0.1:8080`. Login acadêmico: `aluno` / `iceibank-sprint1`.

Cada execução usa segredos aleatórios próprios e, quando necessário, um vhost `iceibank-demo-*`. O encerramento remove apenas o vhost criado pelo comando e encerra apenas os seus processos. Os logs ficam em `.local/apresentacao/`. Uma porta ocupada interrompe a inicialização.

## Gerar o vídeo completo

Pare as agências de ensaios anteriores e mantenha RabbitMQ ativo:

```bash
python -m scripts.gravar_apresentacao
```

Se o navegador do Playwright não estiver disponível, use um Chromium ou Chromium Headless Shell já instalado:

```bash
python -m scripts.gravar_apresentacao --chromium /caminho/chromium-headless-shell
```

Para ensaiar somente um capítulo: `--somente 1`, `--somente 2` ou `--somente 3`. `--saida` permite escolher uma pasta nova. O comando recusa uma pasta de saída existente e verifica os commits históricos antes de gravar.

A saída contém `ICEIBank-3-sprints.mp4`, legendas `.srt`, roteiro com tempos e referências `arquivo:linha`, imagens dos quadros, capturas originais e logs das execuções. Falhas de asserção interrompem a geração; um vídeo completo só é exportado ao terminar todos os cenários selecionados. As capturas históricas versionadas não são usadas no vídeo.

## Conteúdo por capítulo

| Sprint | Operações e resultados registrados |
| --- | --- |
| 1 | Arquitetura REST/MVC; login; criação e consulta de conta; particionamento; depósito; saque; transferência local e HTTP; consulta no destino; saldo insuficiente; ausência e expiração de JWT; valor negativo; histórico e paginação; Lamport e logs; falha remota com débito mantido; conta perdida após reinício |
| 2 | Transferência pelo frontend; publicação e confirmação por consulta; Manager e topologia; persistência de mensagens; ack e rejeição; causalidade e concorrência; destino desligado; mensagem retida; perda da conta no reinício; DLQ; ausência de reaplicação automática |
| 3 | Painel Flutter; login; criação e consulta; depósito e saque; transferências local e remota; histórico; queda e retorno da líder; heartbeat e timeout; depósito sem rede; reconexão e sincronização; conflito real HTTP 409; revisão do aviso; repetição idempotente; cache Hive; histórico de liderança |

As legendas e os trechos de código pertencem à mesma versão da sprint exibida. As respostas registradas em `requisicoes.ndjson` não incluem o token de login. As contas usam apenas dados fictícios de demonstração.

## Alcance da validação mobile

O cliente executado é o próprio projeto Flutter, compilado para Web, em viewport de celular de 420 × 800. Isso permite testar sua interface, Hive, API, fila offline e reconexão. O isolamento offline afeta somente o contexto do navegador; as agências e o RabbitMQ continuam disponíveis para representar outro cliente conectado.

Esse ensaio não comprova execução Android nativa. O ambiente de gravação não possui `/dev/kvm` nem Android SDK. Para validar em aparelho ou emulador, siga [o guia Android](../app_mobile/README.md). Não substitua o cliente Flutter por uma página imitando o app.

## Limitações que aparecem na demonstração

Contas, saldos, histórico consultável e deduplicação permanecem em memória. Reiniciar uma agência perde esses dados; os JSONL permanecem. Bully não replica contas e não altera `id % 3`. A DLQ preserva créditos rejeitados, mas não compensa o débito e não os reaplica automaticamente. Não há Saga/2PC ou idempotência geral de transferências remotas. A deduplicação demonstrada limita-se à sincronização offline na mesma instância.

Codex (OpenAI) apoiou o preparo do ambiente, a automação e o roteiro da gravação. As evidências devem ser avaliadas juntamente com os limites descritos acima.

## Verificação realizada em 23/11/2026

| Versão | Comando | Resultado |
| --- | --- | --- |
| Sprint 1 histórica | `python -m pytest agencia/tests tests/e2e -q` | 99 testes aprovados |
| Sprint 2 histórica | `python -m pytest agencia/tests tests/e2e -q` | 111 testes aprovados |
| Sprint 3 atual | `python -m pytest agencia/tests tests/e2e -q` | 123 testes aprovados |
| Flutter 3.50.1 / Dart 3.14.0 | `flutter analyze` | Sem apontamentos |
| Flutter | `flutter test` | 4 testes aprovados |
| Flutter Web | `flutter build web --release --no-web-resources-cdn --dart-define=ICEIBANK_HOST=127.0.0.1` | Build concluído |

As verificações Python usaram RabbitMQ 4.0.5 real, Erlang 27.3.4.1 e Chromium Headless Shell 156.0.8078.79. O navegador foi informado ao Playwright por um adaptador de execução; os assets oficiais do Swagger foram previamente baixados e atendidos do cache local, pois a CDN não estava disponível diretamente ao navegador. As agências, respostas HTTP e operações bancárias permaneceram reais. Houve apenas o aviso de depreciação existente do `httpx` no TestClient do Starlette. Nenhuma suíte Android nativa foi executada.
