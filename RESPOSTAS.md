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
