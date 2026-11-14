# Sprint 3 · Bully e app Flutter offline-first

## Agências e eleição

As três agências Python continuam usando as portas 4078, 4079 e 4080. Cada
agência inicia uma eleição ao subir e consulta os IDs superiores por
`POST /bully/eleicao`. Se ninguém acima responder, ela anuncia sua liderança
por `POST /bully/coordenador`. As duas mensagens usam o JWT interno existente
e transportam o relógio vetorial no campo `vetorEnvio`.

As seguidoras consultam `GET /bully/lider` da líder atual. Se a líder não
responder ou não confirmar a liderança, iniciam uma eleição. As agências
convergem para o maior ID acessível quando a rede se estabiliza. Se a antiga
líder voltar com o maior ID, ela reassume. O Bully usa timeouts para suspeitar
de falhas, portanto pode haver declarações simultâneas durante uma partição
ou na subida. A liderança é informativa neste sprint. As contas continuam
particionadas por `id % 3`, ficam em memória e os créditos remotos continuam
via RabbitMQ.

Os padrões são 3 segundos entre batimentos e 1 segundo de timeout HTTP. A
funcionalidade adicional permite ajustar os dois valores por instância. Use
valores positivos em segundos e ponto como separador decimal. Exemplo para
configurar antes de iniciar as três agências:

```powershell
$env:BULLY_HEARTBEAT_SEGUNDOS = "1.5"
$env:BULLY_TIMEOUT_SEGUNDOS = "0.5"
```

## Demonstração local

1. Inicie o RabbitMQ e as três agências conforme o [README](../README.md).
2. Confirme que as três instâncias retornam `liderAtual = 2`.

   ```powershell
   Get-Date
   4078..4080 | ForEach-Object { Invoke-RestMethod "http://127.0.0.1:$_/bully/lider" }
   ```

3. Abra o [app Flutter](../app_mobile/README.md) e observe a Agência 2 no
   painel. Encerre o processo da Agência 2, aguarde a troca e consulte as
   portas 4078 e 4079. O app deve mostrar a Agência 1 automaticamente.
   Ao reiniciar a Agência 2, ela retorna à liderança.
4. Na raiz do repositório, rode `node agencia/historico-lideranca.js`. O
   script lê os JSONL de `agencia/data/`. Use `--dados <pasta>` para limitar
   a leitura à pasta de uma execução. A linha do tempo mostra as declarações
   registradas por hora de parede, inclusive as transitórias.

## Sincronização

Consulte `GET /contas/{id}` com o JWT de operador para receber o saldo,
`vetorAtual` e `versaoAgencia`. Envie o depósito ou saque pendente à agência
responsável em `POST /contas/{id}/sincronizar`. Exemplo de corpo:

```json
{
  "tipo": "DEPOSITO",
  "valor": "20.00",
  "vetorConhecido": [4, 0, 0]
}
```

O cliente Flutter também envia `versaoAgencia` e `operacaoId`. A versão
distingue o processo atual de um reinício em que a contagem do vetor pode
reaparecer. O identificador permite repetir o mesmo pedido sem reaplicar
o valor enquanto a instância mantém o estado em memória. A resposta 200
devolve a conta atualizada com o novo vetor. A resposta 409 devolve a relação
causal, os vetores e `contaAtual`, sem aplicar a operação. Para reproduzir
o 409, consulte a conta, faça um depósito por outro cliente e sincronize com
o vetor guardado na consulta anterior.

O app consulta as agências a cada dois segundos em primeiro plano. Quando
a agência responsável volta a responder, envia a fila da conta em ordem.
Em caso de 409, atualiza o saldo confirmado e exige revisão dos pedidos
recusados. Depósitos e saques podem ser registrados offline depois de
consultar a conta. Transferências continuam sendo enviadas online.

## Verificação

Com RabbitMQ local e, para os testes do navegador da Sprint 1, Chromium do
Playwright instalado:

```powershell
$env:RABBITMQ_URL_TESTES = "amqp://guest:guest@127.0.0.1:5672/"
$env:RABBITMQ_MANAGEMENT_URL_TESTES = "http://127.0.0.1:15672"
python -m pytest agencia/tests tests/e2e -q
Set-Location app_mobile
flutter analyze
flutter test
```

Veja [as capturas e a transcrição](../evidencias/sprint3/README.md) e
[as respostas da Sprint 3](../RESPOSTAS.md#sprint-3).
