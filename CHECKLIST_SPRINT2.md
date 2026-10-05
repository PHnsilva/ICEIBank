# Checklist de entrega — Sprint 2

Referência: `docs/Roteiro_Projeto_Sprint2_ICEIBank.md`, seções 2, 4, 6–10.
Linguagem mantida: Python. Os exemplos Node.js do roteiro foram adaptados.

- [x] RabbitMQ real: exchange topic durável `iceibank.eventos`, três filas duráveis e bindings `agencia.<id>.creditar`.
- [x] Mensagens persistentes, confirmação de publicação e ack manual após processamento.
- [x] Relógio vetorial substitui Lamport na aplicação: evento local, envio e recebimento.
- [x] Logs usam `timestampVetorial`; Lamport histórico preservado para consulta.
- [x] Transferência remota publicada e crédito consumido assincronamente; rota REST antiga removida.
- [x] Resiliência: destino encerrado, HTTP 200 na publicação, mensagem retida, reconexão e conta ausente após reinício.
- [x] Linha do tempo por hora de parede, comparação vetorial e pares concorrentes entre agências diferentes.
- [x] Criações independentes concorrentes e débito/crédito causal conferidos no ensaio próprio.
- [x] JWT, frontend, particionamento e histórico verificados na regressão com três processos reais.
- [x] Funcionalidade adicional nova: dead-letter queue por agência, com tentativa limitada, documentação e commit próprio.
- [x] Prints reais: `transferencia-assincrona.png`, `resiliencia-fila.png`, `linha-do-tempo-causal.png` e `funcionalidade-adicional.png`, com Get-Date visível.
- [x] Respostas das seções 6.4, 7.5 e 8.3 e descrição da funcionalidade adicional em `RESPOSTAS.md`.
- [x] Declaração do apoio de IA; compreensão e revisão humana necessárias antes da apresentação.
- [x] Commits pequenos separados por parte, sem alterar datas para simular semanas de desenvolvimento.
- [x] Verificação consolidada final em `evidencias/sprint2/verificacao.txt`: 111 testes aprovados em 04/10/2026.

Os testes e evidências usam RabbitMQ local, alternativa expressamente permitida
na seção 4.1. CloudAMQP é configurável via `RABBITMQ_URL`, mas não foi usada
uma instância CloudAMQP nestes ensaios. Não foi criada conta externa.
