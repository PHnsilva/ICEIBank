# Evidências da Sprint 3

O ensaio em 14 de novembro de 2026 executou três processos Python/FastAPI,
RabbitMQ local e o código Dart do app compilado para Flutter Web em uma janela
de tamanho de celular. O cenário encerrou o processo real da líder e desligou
a rede do cliente no navegador. As contas e os valores são de teste.

As capturas da API e do histórico apresentam as respostas HTTP ou a saída
do script obtidas durante a execução. Cada captura inclui a saída de
`Get-Date` do PowerShell. A [transcrição](execucao.txt) reúne essas saídas e
os passos observados nas telas. Os JSONL em [logs](logs/) permitem reconstruir
a linha do tempo com `node agencia/historico-lideranca.js --dados evidencias/sprint3/logs`.

| Captura | O que conferir |
| --- | --- |
| [Eleição inicial](eleicao-inicial.png) | As três agências informam a Agência 2. |
| [Failover](failover.png) | Depois de encerrar a Agência 2, as duas remanescentes informam a Agência 1. |
| [Histórico de liderança](historico-lideranca.png) | Declarações da eleição inicial, do failover e do retorno da Agência 2. |
| [Liderança no app](app-lider-atual.png) | A Agência 2 no painel com a sessão iniciada. |
| [Failover no app](app-failover.png) | O mesmo painel exibe a Agência 1 sem atualização manual. |
| [Conflito no backend](conflito-sincronizacao.png) | HTTP 409 com vetor conhecido, vetor atual e saldo confirmado. |
| [App offline](app-offline.png) | Um depósito pendente e seu saldo provisório. |
| [App reconectado](app-sincronizacao.png) | O depósito confirmado automaticamente e a fila vazia. |
| [Conflito no app](app-conflito.png) | Saque rejeitado, projeção retirada e saldo confirmado exibido. |
| [Funcionalidade adicional](funcionalidade-adicional.png) | Uma agência aplica heartbeat de 1,5 s e timeout de 0,5 s. |

A suíte Python e de integração passou com **122 testes**. No Flutter, a
análise estática e os **4 testes** do cliente passaram.

A reprodução no Android, inclusive a captura em modo avião, ficou pendente
neste ambiente com virtualização desativada. Os
[passos para executá-la](../../app_mobile/README.md) estão no guia do app.
