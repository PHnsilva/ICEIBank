# Evidências reais — Sprint 2

Ensaios de 04/10/2026, com RabbitMQ 4.3.6/Erlang 28.3 local real e três processos
Python/FastAPI nas portas 4078, 4079 e 4080. A alternativa local é permitida na
seção 4.1 do roteiro; não se afirma execução em CloudAMQP.

| Arquivo | Comprovação |
| --- | --- |
| [transferencia-assincrona.png](transferencia-assincrona.png) | HTTP 200/publicada, logs das duas agências, vetores e crédito confirmado por consulta |
| [resiliencia-fila.png](resiliencia-fila.png) | Destino encerrado, mensagem retida sem consumidores, reinício com conta ausente e falhas de crédito |
| [linha-do-tempo-causal.png](linha-do-tempo-causal.png) | Saída real de `mesclar_logs.py`, criações concorrentes e débito anterior ao crédito |
| [funcionalidade-adicional.png](funcionalidade-adicional.png) | DLQ preserva a mensagem; recriar a conta não reaplica automaticamente o crédito |
| [verificacao.txt](verificacao.txt) | Get-Date, resultado consolidado de backend/navegador/integração e verificação do diff |
| [regressao/fluxo-tres-agencias.json](regressao/fluxo-tres-agencias.json) | Ciclo real pelas três agências, saldos e históricos das APIs |

As quatro capturas obrigatórias mostram **PowerShell real**, executando
`scripts/demonstrar_sprint2.ps1`, com Get-Date visível. A sessão usa ConPTY
(pseudoterminal nativo do Windows) e um visualizador de terminal xterm no
Chromium, conectado somente à saída do processo. O navegador não injeta
respostas, mensagens ou dados. As imagens são screenshots diretos do terminal:
sem edição de pixels, montagem ou reconstrução de logs. O texto exibido deriva
da API, dos arquivos JSONL reais e da inspeção do RabbitMQ Manager.

`transferencia.json`, `resiliencia.json`, `causal.json` e `adicional.json`
registram as asserções e topologia de cada cenário. Os diretórios
`execucao-<cenario>-<dataUTC>/` contêm os logs reais das agências; podem incluir
mais de um ensaio. Os JSONs de resumo e prints correspondem à execução mais
recente do respectivo cenário. Nada é salvo com senha, segredo JWT ou URL
AMQP privada. As contas são fictícias e as chaves são efêmeras.

Na resiliência não se recria a conta antes do consumo: o processo novo começa
sem contas, registra `CREDITO_REMOTO_FALHOU`, tenta a redelivery e envia a
mensagem à DLQ. No ensaio adicional, a conta só é recriada depois de observar a
mensagem na DLQ; seu saldo permanece 1,00. Essa preservação não compensa o débito.

Cada execução usa um vhost aleatório exclusivo e encerra/remove apenas seus
próprios processos/vhost ao terminar. Os registros locais permanecem. A coleta
das estatísticas da fila não consome a mensagem principal; consultar a DLQ
usa `ack_requeue_true` para preservar o material observado.

`regressao/` contém screenshots reais do frontend e Swagger, produzidos pelo
Playwright após suas asserções. A mesma suíte verifica login/401/expiração,
operações bancárias, histórico, layout móvel e o ciclo 0 → 1 → 2 → 0.
Não há mock do broker nesses testes. Dublês existem apenas nos testes unitários
para provocar falha de publicação ou conferir a mensagem produzida.

Para reproduzir, siga o README da raiz, execute `scripts/verificar_sprint2.ps1`
e os quatro comandos `scripts/demonstrar_sprint2.ps1`. Depois capture a tela
do terminal sem editar a saída. As evidências versionadas da Sprint 1 não foram
sobrescritas; permanecem como registro histórico daquela entrega.
