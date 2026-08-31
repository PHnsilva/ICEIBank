# Respostas

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
