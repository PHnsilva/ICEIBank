# Evidências reais — Sprint 1

As quatro capturas de 31/08/2026, referentes às seções 1–10, foram preservadas byte
a byte. As novas capturas são feitas pelo Chromium/Playwright sobre o frontend e
o Swagger reais do FastAPI; não são mockups, não têm respostas simuladas e não
recebem edição de pixels ou substituição de conteúdo.

| Arquivo                                                              | Evidência                                                                |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [transferencia-local.png](transferencia-local.png)                   | Transferência local anterior, preservada                                 |
| [transferencia-entre-agencias.png](transferencia-entre-agencias.png) | Transferência HTTP anterior, preservada                                  |
| [falha-conhecida.png](falha-conhecida.png)                           | Débito mantido após falha remota, preservada                             |
| [linha-do-tempo.png](linha-do-tempo.png)                             | Logs mesclados e empates Lamport, preservada                             |
| [auth-sem-token.png](auth-sem-token.png)                             | Swagger: GET /contas/{id}, sem Authorization → 401                       |
| [auth-com-token.png](auth-com-token.png)                             | Mesma consulta com JWT obtido por login → 200 e saldo                    |
| [auth-token-expirado.png](auth-token-expirado.png)                   | Mesma consulta com JWT cuja validade passou → 401, mensagem de expiração |
| [frontend-login.png](frontend-login.png)                             | Página real de login e seletor de agência                                |
| [frontend-transferencia.png](frontend-transferencia.png)             | Confirmação real de transferência entre agências, valor e saldos         |
| [frontend-erro.png](frontend-erro.png)                               | Saque rejeitado por saldo insuficiente, HTTP 400 e saldo preservado      |
| [funcionalidade-adicional.png](funcionalidade-adicional.png)         | Histórico real após depósito, saque e transferências                     |

## Reprodução e contexto histórico

Estas evidências registram a Sprint 1, integrada pelo [PR #1](https://github.com/PHnsilva/ICEIBank/pull/1). O código atual da `main` já contém a Sprint 2: transferência remota por RabbitMQ e relógio vetorial, em lugar de REST e Lamport.

Para reproduzir o comportamento original, consulte a revisão integrada daquele PR em um checkout separado. Os testes atuais não reproduzem o contrato remoto da Sprint 1 nem atualizam essas capturas históricas.

Para verificar a versão atual, siga o [README principal](../../README.md#testes-resiliência-e-evidências-reais), incluindo broker e vhost de teste. As capturas atuais ficam em [evidencias/sprint2/](../sprint2/README.md).
