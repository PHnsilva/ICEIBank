# Respostas

As seções iniciais abaixo registram a entrega histórica da Sprint 1. A evolução
vigente está na seção **Sprint 2**, ao final; crédito REST e Lamport deixaram de
ser usados pela aplicação atual.

## Seção 6.4 — Relógio lógico de Lamport

1. Ao receber uma mensagem, a agência usa `max(local, recebido) + 1` para garantir
   que o evento de recebimento fique logicamente depois tanto dos eventos que ela já
   observou quanto do evento de envio representado pelo timestamp recebido.
2. Se a Agência 0 está no timestamp 10 e recebe uma mensagem com timestamp 3, seu
   novo timestamp é `max(10, 3) + 1 = 11`.
3. Um valor alto indica que a agência já avançou por muitos eventos locais e/ou
   incorporou timestamps recebidos. Ele não prova que a agência executa mais rápido.
   Da mesma forma, um valor baixo não prova lentidão: a agência pode apenas ter
   processado menos eventos ou recebido menos mensagens. O relógio é lógico, não uma
   medida de duração nem de desempenho.

## Seção 8.3 — Transferências distribuídas

1. Uma transferência local ocorre inteiramente dentro de um processo e não envia
   mensagem para outra agência. Por isso, seus débito e crédito são eventos locais e
   não exigem `ao_enviar()` nem `ao_receber()`.
2. Na falha remota conhecida desta etapa, a conta de origem já foi debitada antes da
   tentativa HTTP. Se o destino estiver indisponível ou rejeitar o crédito, esse débito
   permanece aplicado e um evento `TRANSFERENCIA_FALHOU` é registrado.
3. O dinheiro sai da origem sem a garantia de entrar no destino. Portanto, o sistema
   pode ficar inconsistente e deixar de preservar o saldo total entre as agências.
4. Uma evolução possível é o protocolo de commit em duas fases (2PC), coordenando a
   preparação e a confirmação das duas agências. Outra é uma Saga, na qual uma ação
   compensatória devolveria o valor à origem quando o crédito remoto falhasse.

Essa inconsistência é intencional na Sprint 1 e está prevista para tratamento apenas
na Sprint 4; não há rollback, repetição automática, idempotência, 2PC ou Saga nesta etapa.

## Seção 10 — Linha do tempo unificada

### Observação real dos logs

Na execução de 31 de agosto de 2026, foram observados três eventos independentes de
criação de conta com o mesmo timestamp Lamport 1:

| Agência | Evento | Timestamp Lamport | Hora de parede (UTC) |
| --- | --- | ---: | --- |
| `agencia-0` | `CRIAR_CONTA` da conta 0 | 1 | `2026-08-31T23:43:20.684728Z` |
| `agencia-1` | `CRIAR_CONTA` da conta 1 | 1 | `2026-08-31T23:43:24.852321Z` |
| `agencia-2` | `CRIAR_CONTA` da conta 2 | 1 | `2026-08-31T23:43:26.918822Z` |

Essas criações foram feitas por requisições independentes e não houve mensagem entre
as agências ligando os eventos; por isso, neste cenário observado, eles são concorrentes.
Na captura final, a marca aparece como `[EMPATE x4]` porque a Agência 1 foi reiniciada
durante o ensaio de indisponibilidade. O novo processo começou novamente em 0 e gravou
outra `CRIAR_CONTA` com Lamport 1 às `2026-08-31T23:49:55.189275Z`. Esse evento posterior
não faz parte do trio inicial usado na comparação acima.

O script marcou o empate e usou `horaParede` somente como critério secundário de
apresentação. A ordem de parede Agência 0, Agência 1 e Agência 2 coincidiu com a ordem
exibida. Essa coincidência não demonstra causalidade e dependeria de relógios físicos
adequadamente sincronizados.

### Seção 10.3 — Conclusões conceituais

1. Timestamps Lamport diferentes, sozinhos, não provam que existe relação causal.
2. O relógio de Lamport garante que, se um evento `a` causou um evento `b`, então
   `L(a) < L(b)`. A recíproca não é garantida: `L(a) < L(b)` não prova que `a` causou `b`.
3. Relógios de Lamport sozinhos não conseguem distinguir concorrência com certeza.
4. Relógios vetoriais são motivados porque carregam informação por participante e
   conseguem distinguir ordem causal de eventos concorrentes.

## Seção 11 — Autenticação JWT

1. O login `POST /auth/login` verifica usuário e senha (hash Argon2id) e emite um
   JWT assinado com HS256. O cliente envia `Authorization: Bearer <token>` nas
   operações seguintes. O servidor valida assinatura, algoritmo fixo, emissor,
   destinatário, sujeito, tipo, início de validade e expiração em cada requisição.
2. JWT tem cabeçalho, payload e assinatura. O payload é codificado, não criptografado:
   nunca contém senha ou segredo. A assinatura detecta alterações, mas não oculta
   os dados. `sub` identifica o operador; `iat`, `nbf` e `exp` usam tempo físico UTC,
   não o relógio de Lamport, que não mede duração.
3. O token do operador dura 900 segundos por padrão (`JWT_TTL_SECONDS`). Sem token,
   com assinatura inválida ou após expirar, a API responde 401 com
   `WWW-Authenticate: Bearer`; nenhum saldo ou relógio é alterado. Um novo login
   é necessário após expirar. Não existe refresh token nesta Sprint.
4. Autenticação verifica identidade; autorização define operações permitidas.
   Nesta demonstração há um operador acadêmico que pode administrar todas as
   contas; não se implementa propriedade de conta por usuário. Todas as rotas de
   contas e transferências exigem JWT. Login, frontend, configuração pública das
   agências e documentação OpenAPI são públicos e não expõem dados bancários.
5. As agências usam uma chave diferente da chave de usuários e tokens de serviço
   de 30 segundos, com sujeito da origem, audiência exclusiva do destino e SHA-256
   do caminho e corpo da mensagem dentro da assinatura. O destino confere origem,
   destino e integridade antes de avançar Lamport ou creditar. Um token de usuário
   não autoriza crédito remoto; o JWT do usuário não é repassado ao destino.
6. Segredos aleatórios ficam no `.env` ignorado pelo Git, iguais nas três instâncias,
   e a aplicação recusa configuração ausente/fraca ou chaves iguais. A senha só
   fica como hash Argon2id. `scripts/configurar_demo.py` gera chaves sem sobrescrever
   um `.env` existente. A senha de demonstração é pública e exclusiva para uso local.
7. As três agências escutam somente em loopback. A assinatura autentica as mensagens,
   mas HTTP não fornece confidencialidade: em máquinas distintas seria obrigatório
   usar HTTPS/TLS e gerir/rotacionar segredos. Chaves compartilhadas pressupõem
   confiança entre as três agências. Tokens Bearer roubados podem ser reutilizados
   até expirar; não há revogação, proteção contra replay nem idempotência nesta
   etapa, coerentemente com o escopo de consistência das Sprints seguintes.

Referências de implementação: [FastAPI — JWT e hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
e [PyJWT — validação de claims](https://pyjwt.readthedocs.io/en/stable/api.html).

## Seção 12 — Frontend web e decisões de projeto

1. O frontend usa HTML, CSS e JavaScript sem framework e é servido pelo próprio
   FastAPI em `/`. Assim, as três agências oferecem a mesma interface e não é
   necessário um quarto servidor ou processo de build. O navegador descobre o
   mapeamento fixo em `/config`; a seleção altera a URL da API chamada.
2. O fluxo é login → seleção da agência → consulta da conta → operação. Há depósito,
   saque, transferência local, transferência entre agências e abertura de conta
   de demonstração. O particionamento continua `id % 3`; o frontend mostra a agência
   do destino e verifica o tipo de transferência, mas a API permanece responsável
   por validar conta, valor e saldo. Valores são enviados como strings decimais;
   a formatação de moeda no navegador não participa dos cálculos do servidor.
3. O JWT fica somente em memória JavaScript. Recarregar a página ou sair descarta
   a sessão; não se grava token ou senha em localStorage, URLs ou logs. A senha é
   limpa após login. A expiração também é observada na interface e qualquer 401
   da API encerra a sessão e apresenta uma mensagem para entrar novamente.
4. Erros HTTP são exibidos com status, `detail` e campos de validação. Falhas de
   rede têm mensagem própria e não são repetidas automaticamente. Após erro de
   movimentação, a interface tenta atualizar o saldo, inclusive no 502 conhecido
   em que o débito permanece aplicado. Se não conseguir consultar, limpa o saldo
   para não apresentar um valor antigo como atual.
5. Controles ficam desabilitados durante cada requisição para evitar envio duplo e
   troca de agência em andamento. Trocar a agência ou editar o número limpa a conta
   selecionada. As mensagens e os nomes usam `textContent`, evitando interpretar
   HTML recebido da API. Há labels, foco visível, mensagens acessíveis, layout móvel
   e estados de sucesso/erro. CORS permite apenas as origens locais das três agências.
6. MVC permanece: estado/modelos em `estado_agencia.py`, regras HTTP nos controllers,
   serviços de autenticação/relógio/registro e apresentação em `agencia/frontend`.
   Evitou-se adicionar React/Node/build porque formulários simples e Fetch atendem
   ao escopo sem duplicar a lógica bancária existente.

## Funcionalidade adicional obrigatória — Histórico por conta

**Escolha e valor:** o operador pode conferir como o saldo mudou, identificar crédito
local/remoto e perceber uma transferência que falhou depois do débito. O saldo
isolado não explica esses acontecimentos; um histórico por conta torna-os verificáveis.

**Endpoint:** `GET /contas/{id}/historico?offset=0&limite=50`, protegido pelo JWT do
operador. Retorna `idConta`, `saldoAtual`, `eventos`, `total`, `offset` e `limite`.
Cada evento contém agência, tipo, `timestampLamport`, `horaParede` UTC e detalhes
(valor, saldo após o evento e identificadores, conforme o tipo). A ordem é a ordem
de registro local, com timestamps Lamport crescentes. O limite permitido é 1–100;
offset negativo ou limite inválido retorna 422; conta ausente retorna 404.

**Implementação:** `RegistroEventos` indexa os eventos já registrados, sem gerar
outro evento Lamport nem duplicar a lógica de movimentação. Débito pertence somente
à origem; crédito pertence somente ao destino. A consulta usa o lock do estado e
obtém um snapshot copiado do registrador. Assim, o saldo e a lista são consistentes
no instante da consulta. Falhas remotas aparecem como débito seguido de falha,
preservando a limitação intencional da Sprint 1.

**Persistência:** o histórico consultável é do processo atual, assim como as contas
em memória. Os arquivos JSONL históricos permanecem no disco, mas não são carregados
como extrato de uma conta recriada após reiniciar: isso misturaria saldos de execuções
diferentes. O consumo de memória cresce com os eventos; persistência e retenção
ficam para uma evolução do projeto, sem introduzir banco de dados nesta Sprint.

**Interface e comprovação:** a seção Histórico permite consultar e carregar mais
eventos, mostra data/hora local, tipo, valor e saldo do evento. Ao trocar conta ou
agência, ou movimentar o saldo, a lista é limpa e pode ser consultada novamente.
Testes em `agencia/tests/test_historico.py` cobrem isolamento, paginação, autorização,
rejeições, crédito remoto, falha remota e reinício. O teste de navegador
`test_historico_conta_com_endpoint_real` usa as três agências reais e produz
`evidencias/sprint1/funcionalidade-adicional.png`.

## Revisão final e compatibilidade com as seções 1–10

A revisão identificou que uma transferência para destino **local** inexistente já
restaurava o saldo, mas deixava somente o evento de débito no log. Foi acrescentado
`ESTORNO_LOCAL` com saldo restaurado para que o novo histórico seja fiel ao estado.
O status 404 e o saldo final permanecem iguais; a falha **remota** continua sem
restauração, como exigido na Sprint 1. Não foi introduzida compensação distribuída.

Também foi impedido que uma resposta atrasada repopule a conta após a sessão
expirar, e mensagens de agência com corpo não-objeto passam a ser rejeitadas com
401 antes do relógio. Os testes incluem falha remota real na interface (502 e
saldo debitado) e expiração durante uma consulta. Para o timer de frontend, o teste
avança somente o relógio do navegador; a evidência JWT expirado usa espera real.

O checklist operacional está em `CHECKLIST_SPRINT1.md` e o método das capturas em
`evidencias/sprint1/README.md`. O enunciado original da disciplina não está presente
no repositório; as respostas acima cobrem os requisitos fornecidos na solicitação
de continuação. O vídeo de apresentação foi expressamente excluído desta entrega.

Verificação final de 07/09/2026: **99 testes passaram**, sendo 90 de backend e 9 de
navegador. O ciclo real pelas três agências foi confirmado pelas APIs, com saldo
total final de R$ 415,00. Saída, datas e saldos estão em
`evidencias/sprint1/verificacao.txt` e `evidencias/sprint1/fluxo-tres-agencias.json`.
Permanece um aviso de depreciação do TestClient/Starlette já presente na base;
nenhum teste falhou. As sete novas capturas foram conferidas visualmente.

---

## Sprint 2 — Parte B, seção 6.4: relógio vetorial

1. Com dez agências, cada vetor passa de três para dez contadores. O tamanho da
   mensagem e o trabalho de mesclar/comparar vetores crescem linearmente com o
   número de participantes. Dez posições são pequenas neste exercício, mas um
   sistema com muitos participantes precisaria considerar custo de rede,
   armazenamento e associação estável entre posições e processos.
2. `[3,1,0]` aconteceu antes de `[3,2,0]`: a primeira lista é menor ou igual
   posição a posição, e há desigualdade estrita na posição 1. A comparação do
   código retorna `ANTES`.
3. `[3,1,0]` e `[1,3,0]` são concorrentes: o primeiro é maior na posição 0,
   enquanto o segundo é maior na posição 1. Nenhum domina o outro; a comparação
   retorna `CONCORRENTES`.

## Sprint 2 — Parte C, seção 7.5: mensageria e resiliência

1. No ensaio real de 04/10/2026, a conta 1 foi criada com 100,00 e a Agência 1
   encerrada. A Agência 0 publicou 15,00 e respondeu HTTP 200 com
   `status=publicada`, ficando com 85,00. O RabbitMQ manteve a mensagem na fila
   sem consumidores. Quando a Agência 1 voltou, `GET /contas/1` retornou 404:
   o novo processo não carregou as contas do anterior. O consumidor recebeu o
   vetor `[3,0,0]`, registrou `CREDITO_REMOTO_FALHOU` com motivo
   `conta não encontrada` e, após uma nova entrega imediata malsucedida, rejeitou
   definitivamente a mensagem. A DLQ preservou o crédito com
   `x-death.reason=rejected`. A mensagem foi entregue; a falha foi a perda do
   estado em memória, não o desaparecimento da publicação. Os resultados reais
   estão em `evidencias/sprint2/resiliencia.json`, nos logs e no print correspondente.
2. Na Sprint 1, o destino desligado fazia a chamada HTTP falhar, retornando 502
   após o débito. Agora o destino pode estar desligado e a publicação ainda
   funcionar: a fila durável retém a mensagem persistente até reconectar.
   Entretanto, publicação não confirma crédito, e durabilidade do broker não
   persiste as contas. Ainda pode haver dinheiro debitado sem crédito, e falhas
   de publicação/acknowledgement podem deixar resultados incertos ou provocar
   redelivery. Não há compensação distribuída, persistência de contas ou
   garantia de processamento exatamente uma vez nesta etapa.
3. O consumidor não recebe JWT HTTP; a autenticação ocorre na conexão AMQP, e
   as permissões do broker delimitam quem pode configurar, publicar e consumir.
   Isso constitui uma fronteira de confiança, não uma ausência total de
   autenticação. Quem obtiver credenciais com permissão de publicação poderá
   produzir créditos: o consumidor valida valores, vetor, origem e partição,
   mas não prova criptograficamente a identidade de cada produtor. No ensaio,
   o RabbitMQ usa `guest` somente em loopback e um vhost aleatório exclusivo.
   Para CloudAMQP, a URL AMQPS fica no ambiente/.env, sem ser versionada;
   credenciais e permissões devem ser restritas aos participantes autorizados.
   Tokens JWT de usuário continuam obrigatórios nas operações REST bancárias.

## Sprint 2 — Parte D, seção 8.3: linha do tempo causal

1. O vetor registra conhecimento por participante. Local e envio incrementam
   a posição da agência; recebimento faz máximo componente a componente e
   incrementa a posição local. Assim, `V1 < V2` em ordem parcial representa
   precedência causal, enquanto dois vetores incomparáveis representam
   concorrência. O escalar Lamport não carrega essas diferenças por participante;
   sua ordem estrita não prova causalidade na direção inversa.
2. No ensaio próprio, `CRIAR_CONTA` da Agência 0 com `[1,0,0]` e
   `CRIAR_CONTA` da Agência 1 com `[0,1,0]` apareceram como concorrentes.
   Foram requisições independentes, sem transferência ligando as criações.
   A hora de parede exibida em sequência não cria causalidade. Já o débito
   `[2,0,0]` aconteceu antes do crédito remoto `[3,2,0]`, e esse par não foi
   listado como concorrente. `evidencias/sprint2/causal.json` registra as
   verificações; `linha-do-tempo-causal.png` mostra a saída do script Python.
3. Comparar todos os pares custa O(n² × a), em que `a` é o número de agências
   (três fixas aqui). Milhões de eventos gerariam um volume impraticável de
   comparações e de saída. É possível restringir a investigação a uma execução,
   intervalo, transação ou conjunto de participantes; manter índices vetoriais
   e fronteiras de eventos; e consultar um grafo causal conforme a necessidade.
   Dividir a análise em janelas exige preservar as dependências entre elas.
   Se a pergunta exigir enumerar todos os pares concorrentes, a própria resposta
   pode ter tamanho quadrático: um índice não elimina esse custo de saída.

## Sprint 2 — Funcionalidade adicional: fila de mensagens não processadas

O RabbitMQ declara uma exchange topic durável `iceibank.nao-processadas` e uma
DLQ durável por agência, `fila-agencia-<id>.nao-processadas`. Cada fila principal
tem `x-dead-letter-exchange=iceibank.nao-processadas`; a routing key original
`agencia.<id>.creditar` direciona a mensagem para a DLQ correspondente.

Crédito bem processado recebe ack manual. Se a mensagem é válida, mas a conta
não existe, o recebimento e a falha são registrados e o consumidor rejeita com
requeue na primeira entrega. Se a nova entrega também falhar (`redelivered`),
rejeita sem requeue: o broker move a mensagem para a DLQ. Mensagens inválidas
também têm esse limite; erros internos inesperados seguem diretamente à DLQ.
Não há ciclo infinito nem consumidor automático da DLQ. Uma mensagem já marcada
como redelivery após interrupção também não recebe uma terceira tentativa.

O ensaio adicional confirmou mensagem persistente (`delivery_mode=2`) e
`x-death.reason=rejected`. Depois de recriar a conta 1 com 1,00, o saldo ficou
em 1,00: a mensagem retida na DLQ não foi reaplicada silenciosamente. A DLQ
preserva material para diagnóstico, mas não devolve dinheiro à origem nem
garante consistência. Reprocessamento com idempotência e ações compensatórias
permanece fora do escopo desta sprint.

Implementação em `agencia/app/services/mensageria.py`; teste real em
`tests/e2e/test_sprint2.py`; demonstração em `scripts/demonstrar_sprint2.ps1 adicional`;
evidências em `evidencias/sprint2/adicional.json` e `funcionalidade-adicional.png`.
A implementação adicional tem commit próprio.

## Sprint 2 — Continuidade e transparência

Python/FastAPI, MVC, particionamento, Decimal, JWT, frontend e histórico foram
mantidos. O frontend informa **publicação assíncrona** e orienta consultar o
destino; não apresenta saldo de destino como se o crédito já estivesse aplicado.
Os testes usam três servidores reais e RabbitMQ real. Dublês são usados somente
nos testes isolados de backend; o cenário de integração e os prints não dependem deles.

Foi utilizado **Codex (OpenAI)** para apoiar implementação, testes, documentação
e captura das evidências. Os resultados documentados vêm das execuções reais
registradas. O autor deve revisar o código e compreender as decisões antes da
apresentação e entrega; esta declaração não afirma que essa revisão humana já ocorreu.

Referências consultadas: [aio-pika — integração assíncrona](https://docs.aio-pika.com/quick-start.html),
[RabbitMQ — confirmações](https://www.rabbitmq.com/docs/confirms) e
[RabbitMQ — dead-letter exchanges](https://www.rabbitmq.com/docs/dlx).
