# Checklist de verificação — Sprint 1

Registro histórico da Sprint 1: o PR #1 foi posteriormente integrado à `main`.
A aplicação atual evolui na Sprint 2, verificada em `CHECKLIST_SPRINT2.md`.

Este checklist operacional reúne os requisitos da solicitação de continuação e os
itens já documentados no repositório. O enunciado original da disciplina não está
versionado; a numeração interna de perguntas não foi inventada. As respostas
existentes das seções 6.4, 8.3 e 10 foram preservadas.

## Base concluída — seções 1–10

- [x] Branch `sprint1/desenvolvimento` e PR existente para `main` preservados.
- [x] Python/FastAPI, MVC e contas em memória.
- [x] Três agências; offset 78; portas 4078, 4079 e 4080.
- [x] Particionamento `id_conta % 3`.
- [x] Relógio Lamport local, envio e recebimento `max(local, recebido) + 1`.
- [x] Logs JSONL com agência, tipo, Lamport, hora UTC e detalhes.
- [x] Criar conta, consultar saldo, depositar e sacar; validações monetárias.
- [x] Transferência local e entre agências via HTTP.
- [x] Falha remota conhecida: 502, débito mantido e evento de falha.
- [x] Mesclar logs, ordenar por Lamport e destacar empates.
- [x] Respostas e quatro capturas existentes mantidas.
- [x] Os 56 testes originais continuam passando com login real nas fixtures.

## Seção 11 — JWT

- [x] Login verifica credenciais; senha armazenada como hash Argon2id.
- [x] JWT assinado HS256, com algoritmo fixo, sujeito, emissor, audiência e validade.
- [x] Token de operador expira; TTL configurável, padrão 900 segundos.
- [x] Todas as rotas bancárias, inclusive histórico, protegidas.
- [x] 401 para ausência, token inválido, expirado ou credencial de login inválida.
- [x] `WWW-Authenticate: Bearer`; requisições rejeitadas não alteram saldo/Lamport.
- [x] Agências usam chave separada e JWT de serviço de 30 segundos.
- [x] Origem, audiência do destino e caminho/corpo assinados e conferidos.
- [x] Token de usuário não autoriza crédito remoto; segredo não fica no frontend.
- [x] Configuração sem segredos válidos falha; `.env` ignorado pelo Git.
- [x] Respostas e limites de segurança em `RESPOSTAS.md`.
- [x] Capturas reais sem token, com token e token expirado.

## Seção 12 — Frontend

- [x] Login e logout funcionais, token somente em memória, expiração/401 visíveis.
- [x] Seleção entre as três agências.
- [x] Consulta de saldo, depósito e saque.
- [x] Transferência local e entre agências.
- [x] Erros HTTP, validação e rede visíveis; sem repetição automática.
- [x] Conta/saldo limpos ao trocar seleção; controles bloqueados durante envio.
- [x] Saldo atualizado após operação e tentativa de atualização após falha.
- [x] Layout móvel, labels e mensagens acessíveis, escape de conteúdo da API.
- [x] Capturas de login, transferência e erro.
- [x] Respostas e decisões de frontend documentadas.

## Funcionalidade adicional obrigatória

- [x] Histórico de transações por conta em endpoint próprio, autenticado.
- [x] Ordem, valores, saldos, timestamps e isolamento entre contas.
- [x] Paginação com validação de limites.
- [x] Consulta e carregamento de páginas na interface.
- [x] Documentação e justificativa.
- [x] Testes de endpoint e navegador; evidência `funcionalidade-adicional.png`.

## Entrega

- [x] Backend e frontend exercitados com três processos reais nas portas oficiais.
- [x] Testes cobrem erros e mantêm explícita a inconsistência da Sprint 1.
- [x] Evidências de navegador são screenshots reais sem composição/edição.
- [x] Evidências anteriores de terminal preservadas; data registrada na verificação.
- [x] Verificação consolidada final registrada em `evidencias/sprint1/verificacao.txt`: 99 testes passaram (90 backend, 9 navegador), em 07/09/2026.
- [x] Commits finais publicados e PR atualizado após a revisão.
- [ ] Vídeo de apresentação — **excluído do escopo por solicitação**.

O PR #1 está mesclado no GitHub. A pendência de vídeo acima é o registro do escopo
daquela entrega; sua apresentação externa não foi verificada nesta evolução.
