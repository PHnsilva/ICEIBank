# Sprint 3 · Eleição de líder e aplicativo Flutter

Implementação inicial baseada na visão geral do roteiro. O algoritmo, o fluxo
móvel, a demonstração e os entregáveis serão confrontados com o roteiro completo.

## Eleição entre as três agências

As agências continuam nas portas 4078, 4079 e 4080 do mesmo computador. Cada
processo começa como seguidor e espera um batimento. Quando o prazo aleatório
expira, o processo inicia uma candidatura em um novo mandato e solicita votos
às outras agências. Dois votos formam uma maioria. Cada processo registra seu
mandato e voto em arquivo, inclusive para recuperar o estado após um reinício.

A líder envia batimentos HTTP e deixa de se anunciar como líder quando perde
a confirmação de maioria. As mensagens entre agências usam o JWT de serviço,
assinado para o destino, o caminho e o corpo. As três instâncias precisam usar
a mesma configuração de autenticação.

O protocolo usa apenas a parte de eleição inspirada em Raft. O líder coordena
o grupo, enquanto cada conta continua na partição calculada por `id % 3`.
Contas e saldos ficam em memória. Ao encerrar uma agência, sua partição fica
indisponível e volta vazia após o reinício. O RabbitMQ continua transportando
os créditos remotos. A seção 5.2 do [artigo de Raft](https://raft.github.io/raft.pdf)
descreve a eleição que serviu de referência.

## Demonstração local

1. Prepare o Python e o RabbitMQ conforme o [README](../README.md) e inicie as
   três agências com `python agencia/executar.py` e os respectivos `AGENCIA_ID`.
2. Consulte o estado de cada processo no PowerShell.

   ```powershell
   4078..4080 | ForEach-Object {
       Invoke-RestMethod "http://127.0.0.1:$_/cluster/status"
   }
   ```

3. Encerre a agência cujo `papel` é `lider`. Depois de alguns segundos,
   consulte as outras duas portas. As duas devem informar o mesmo `liderId`
   e um mandato superior ao anterior. Reinicie a agência encerrada para
   observar a volta como seguidora.
4. Abra o [app Android](../mobile/README.md) para acompanhar o estado do grupo
   e realizar operações nas agências disponíveis. A confirmação de publicação
   de uma transferência remota antecede a confirmação do crédito.

## Testes

Com o RabbitMQ local iniciado e as portas das agências livres:

```powershell
$env:RABBITMQ_URL_TESTES = "amqp://guest:guest@127.0.0.1:5672/"
$env:RABBITMQ_MANAGEMENT_URL_TESTES = "http://127.0.0.1:15672"
python -m pytest agencia/tests tests/e2e/test_sprint2.py tests/e2e/test_sprint3.py -q
```

O teste de eleição usa três processos reais, encerra a líder, confere a nova
liderança e verifica o retorno da antiga líder e a perda de maioria. Os testes
do cliente Flutter verificam o roteamento por partição, a sessão e o tratamento
de falha em uma operação bancária.

## Uso de IA

Codex (OpenAI) apoiou o desenho e a implementação da eleição, do cliente
Flutter, dos testes e da documentação. O autor deve revisar o código e saber
explicar a eleição, os limites da recuperação e o fluxo de cada operação.
