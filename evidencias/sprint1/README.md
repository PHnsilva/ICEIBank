# Evidências reais — Sprint 1

As quatro capturas de 31/08/2026, referentes às seções 1–10, foram preservadas byte
a byte. As novas capturas são feitas pelo Chromium/Playwright sobre o frontend e
o Swagger reais do FastAPI; não são mockups, não têm respostas simuladas e não
recebem edição de pixels ou substituição de conteúdo.

| Arquivo | Evidência |
| --- | --- |
| [transferencia-local.png](transferencia-local.png) | Transferência local anterior, preservada |
| [transferencia-entre-agencias.png](transferencia-entre-agencias.png) | Transferência HTTP anterior, preservada |
| [falha-conhecida.png](falha-conhecida.png) | Débito mantido após falha remota, preservada |
| [linha-do-tempo.png](linha-do-tempo.png) | Logs mesclados e empates Lamport, preservada |
| [auth-sem-token.png](auth-sem-token.png) | Swagger: GET /contas/{id}, sem Authorization → 401 |
| [auth-com-token.png](auth-com-token.png) | Mesma consulta com JWT obtido por login → 200 e saldo |
| [auth-token-expirado.png](auth-token-expirado.png) | Mesma consulta com JWT cuja validade passou → 401, mensagem de expiração |
| [frontend-login.png](frontend-login.png) | Página real de login e seletor de agência |
| [frontend-transferencia.png](frontend-transferencia.png) | Confirmação real de transferência entre agências, valor e saldos |
| [frontend-erro.png](frontend-erro.png) | Saque rejeitado por saldo insuficiente, HTTP 400 e saldo preservado |
| [funcionalidade-adicional.png](funcionalidade-adicional.png) | Histórico real após depósito, saque e transferências |

## Reprodução

Execute a preparação descrita no README e, com as portas 4078–4080 livres:

```powershell
Get-Date
python -m pytest agencia/tests tests/e2e -q
```

`tests/e2e/conftest.py` inicia três servidores isolados com chaves aleatórias,
senha de teste, contas de demonstração e logs temporários. Os processos são
encerrados ao fim. Identificadores de conta podem variar conforme a seleção de
testes; as asserções verificam os mesmos resultados monetários.

`test_frontend.py` captura as quatro telas somente depois de conferir as respostas
reais. O ciclo completo 0 → 1 → 2 → 0 termina com saldos 85,00 / 110,00 / 105,00 e
115,00 na segunda conta local, preservando o total de 415,00 após depósito de 25,00
e saque de 10,00 sobre quatro saldos iniciais de 100,00.

`test_auth_evidencias.py` opera o Swagger e captura o bloco expandido da operação,
incluindo URL, requisição, status, corpo e cabeçalhos reais. O token válido vem de
`POST /auth/login`. O token curto usa a mesma função e chave de emissão dos servidores
de teste, com validade de um segundo; o teste espera dois segundos de tempo real
antes de enviar. Não altera o relógio do computador ou desliga a validação do JWT.
As chaves efêmeras são descartadas no fim da suíte; não são as chaves do `.env` local.

As capturas novas de autenticação são de **navegador**, com o cabeçalho HTTP `Date`
visível. Não há terminal reconstruído. `Get-Date` fica no transcript da execução
PowerShell em `verificacao.txt`; as evidências antigas de terminal permanecem intactas.

Alguns testes adicionais de frontend simulam falha de rede/401 para conferir a
recuperação da interface. Eles não produzem as capturas de autenticação e não
substituem os testes HTTP reais. A suíte de backend também valida tokens expirados,
assinaturas alteradas e mensagens de serviço inválidas.
