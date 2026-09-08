"use strict";
const $ = (selector) => document.querySelector(selector);
const agencia = $("#agencia");
const mensagem = $("#mensagem");
let token = null;
let agencias = [];
let contaAtual = null;
let expira = null;

function avisar(texto, erro = false) {
  mensagem.textContent = texto;
  mensagem.classList.toggle("error", erro);
  mensagem.setAttribute("role", erro ? "alert" : "status");
  mensagem.hidden = false;
}
function limparConta() {
  contaAtual = null;
  $("#saldo").textContent = "—";
  $("#titular").textContent = "Selecione uma conta para consultar.";
  $("#origem-info").textContent = "Consulte a conta antes de movimentar.";
  limparHistorico();
}
function sair() {
  token = null;
  clearTimeout(expira);
  limparConta();
  $("#login-panel").hidden = false;
  $("#banco-panel").hidden = true;
  $("h1").textContent = "Olá. Vamos começar?";
  $("#login-form").reset();
}
async function api(caminho, corpo) {
  const tokenDaRequisicao = token;
  const base = agencias.find((item) => item.id === Number(agencia.value)).url;
  let resposta;
  try {
    resposta = await fetch(base + caminho, {
      method: corpo === undefined ? "GET" : "POST",
      headers: { ...(corpo === undefined ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    throw new Error("Não foi possível comunicar com a agência selecionada. Verifique se ela está em execução. Se enviou uma operação, consulte o saldo antes de tentar novamente.");
  }
  const dados = await resposta.json();
  if (tokenDaRequisicao && tokenDaRequisicao !== token) {
    throw new Error("Sessão encerrada. Faça login novamente.");
  }
  if (!resposta.ok) {
    if (resposta.status === 401) sair();
    const campos = (dados.erros || []).map((e) => `${e.campo}: ${e.mensagem}`).join(" ");
    const erro = new Error(`HTTP ${resposta.status} — ${dados.detail || "Erro na API."}${campos ? " " + campos : ""}`);
    erro.status = resposta.status;
    throw erro;
  }
  return dados;
}
async function executar(acao) {
  const controles = [...document.querySelectorAll("button, input, select")];
  controles.forEach((el) => { el.disabled = true; });
  mensagem.hidden = true;
  try { await acao(); } catch (erro) { avisar(erro.message, true); }
  finally { controles.forEach((el) => { el.disabled = false; }); }
}
function moeda(valor) {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function mostrarConta(conta) {
  limparHistorico();
  contaAtual = conta;
  $("#conta").value = conta.id;
  $("#titular").textContent = `${conta.nomeAluno} · Conta ${conta.id} · Agência ${agencia.value}`;
  $("#saldo").textContent = moeda(conta.saldo);
  $("#origem-info").textContent = `Conta de origem: ${conta.id} · Agência ${agencia.value}`;
}

let historicoOffset = 0;
function limparHistorico() {
  historicoOffset = 0;
  $("#historico-itens").replaceChildren();
  $("#historico-tabela").hidden = true;
  $("#historico-mais").hidden = true;
  $("#historico-info").textContent = "Consulte o histórico da conta selecionada para ver as movimentações atuais.";
}
const tiposEvento = {
  CRIAR_CONTA: "Abertura de conta", DEPOSITO: "Depósito", SAQUE: "Saque",
  TRANSFERENCIA_DEBITO: "Transferência enviada · débito",
  TRANSFERENCIA_CREDITO: "Transferência local recebida",
  TRANSFERENCIA_CREDITO_REMOTO: "Transferência de outra agência recebida",
  TRANSFERENCIA_FALHOU: "Transferência falhou · débito mantido",
  ESTORNO_LOCAL: "Débito local restaurado",
};
async function carregarHistorico(reiniciar) {
  if (!contaAtual) throw new Error("Consulte uma conta antes de carregar o histórico.");
  if (reiniciar) limparHistorico();
  const resultado = await api(`/contas/${contaAtual.id}/historico?offset=${historicoOffset}&limite=20`);
  for (const evento of resultado.eventos) {
    const linha = document.createElement("tr");
    const d = evento.detalhes;
    const valores = [new Date(evento.horaParede).toLocaleString("pt-BR"), tiposEvento[evento.tipo] || evento.tipo,
      d.valor ? moeda(d.valor) : "—", d.saldo ? moeda(d.saldo) : "—"];
    valores.forEach((valor) => { const cell = document.createElement("td"); cell.textContent = valor; linha.append(cell); });
    $("#historico-itens").append(linha);
  }
  historicoOffset += resultado.eventos.length;
  $("#historico-tabela").hidden = resultado.total === 0;
  $("#historico-mais").hidden = historicoOffset >= resultado.total;
  $("#historico-info").textContent = `Conta ${resultado.idConta} · ${historicoOffset} de ${resultado.total} eventos · Saldo atual: ${moeda(resultado.saldoAtual)}. Histórico desta execução, em ordem cronológica.`;
}
$("#historico-atualizar").addEventListener("click", () => executar(() => carregarHistorico(true)));
$("#historico-mais").addEventListener("click", () => executar(() => carregarHistorico(false)));
$("#login-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const dados = Object.fromEntries(new FormData(event.target));
  executar(async () => {
    const login = await api("/auth/login", dados);
    token = login.access_token;
    $("#login-form").reset();
    $("#login-panel").hidden = true;
    $("#banco-panel").hidden = false;
    $("h1").textContent = "Sua conta, em movimento.";
    $("#sessao").textContent = `Operador ${dados.usuario} · Sessão autenticada`;
    expira = setTimeout(() => { sair(); avisar("Sessão expirada. Faça login novamente.", true); }, login.expires_in * 1000);
  });
});
$("#sair").addEventListener("click", () => { sair(); avisar("Você saiu da sua conta."); });
agencia.addEventListener("change", () => { limparConta(); $("#conta").value = ""; mensagem.hidden = true; });
$("#conta").addEventListener("input", limparConta);
$("#consulta-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const id = $("#conta").value;
  executar(async () => { limparConta(); mostrarConta(await api(`/contas/${id}`)); });
});
$("#criar-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const dados = Object.fromEntries(new FormData(event.target));
  dados.id = Number(dados.id);
  executar(async () => { mostrarConta(await api("/contas", dados)); avisar(`Conta ${dados.id} criada com sucesso.`); event.target.reset(); });
});
$("#operacao").addEventListener("change", () => {
  const transferencia = ["transferir", "remota"].includes($("#operacao").value);
  $("#destino-fields").hidden = !transferencia;
  $("[name=destino]").required = transferencia;
});
$("[name=destino]").addEventListener("input", (event) => {
  $("#destino-agencia").textContent = event.target.value === "" ? "Informe o destino para identificar a agência." : `Agência de destino: ${Number(event.target.value) % 3}`;
});
$("#operacao-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const dados = Object.fromEntries(new FormData(event.target));
  executar(async () => {
    if (!contaAtual) throw new Error("Consulte a conta antes de movimentar.");
    const id = contaAtual.id;
    const transferencia = ["transferir", "remota"].includes(dados.operacao);
    if (transferencia) {
      const local = Number(dados.destino) % 3 === Number(agencia.value);
      if (local !== (dados.operacao === "transferir")) throw new Error("A conta de destino não corresponde ao tipo de transferência selecionado.");
    }
    let resultado;
    try {
      resultado = await api(transferencia ? "/transferencias" : `/contas/${id}/${dados.operacao}`,
        transferencia ? { idOrigem: id, idDestino: Number(dados.destino), valor: dados.valor } : { valor: dados.valor });
    } catch (erro) {
      if (token) { try { mostrarConta(await api(`/contas/${id}`)); } catch { limparConta(); } }
      throw erro;
    }
    // A resposta da mutação já confirma o saldo: não transformar uma falha de leitura em falha da operação.
    mostrarConta(transferencia ? { ...contaAtual, saldo: resultado.saldoOrigem } : resultado);
    avisar(transferencia ? `${resultado.mensagem}\nConta ${id} → Conta ${dados.destino} · ${moeda(resultado.valor)}\nSaldo da origem: ${moeda(resultado.saldoOrigem)} · Saldo do destino: ${moeda(resultado.saldoDestino)}` : `${dados.operacao === "depositar" ? "Depósito" : "Saque"} realizado com sucesso. Saldo: ${moeda(resultado.saldo)}.`);
  });
});
fetch("/config").then((r) => { if (!r.ok) throw new Error(); return r.json(); }).then((config) => {
  agencias = config.agencias;
  agencias.forEach((item) => { const option = document.createElement("option"); option.value = item.id; option.textContent = `Agência ${item.id} · ${4078 + item.id}`; agencia.append(option); });
  agencia.value = config.agenciaAtual;
  agencia.disabled = false;
}).catch(() => { avisar("Não foi possível carregar as agências. Recarregue a página.", true); $("#login-form button").disabled = true; });
