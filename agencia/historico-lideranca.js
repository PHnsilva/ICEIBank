const fs = require('node:fs');
const path = require('node:path');

const tipos = new Set([
  'ELEICAO_INICIADA', 'ELEICAO_RECEBIDA', 'TORNOU_LIDER',
  'LIDER_ANUNCIADO', 'LIDER_NAO_RESPONDEU',
]);

function carregarEventos(pasta) {
  const eventos = [];
  const arquivos = fs.readdirSync(pasta).filter((nome) => nome.endsWith('.jsonl'));
  for (const arquivo of arquivos.sort()) {
    const linhas = fs.readFileSync(path.join(pasta, arquivo), 'utf8').split(/\r?\n/);
    for (const [indice, linha] of linhas.entries()) {
      if (!linha.trim()) continue;
      try {
        const evento = JSON.parse(linha);
        if (!tipos.has(evento.tipo)) continue;
        if (!Number.isFinite(Date.parse(evento.horaParede))) throw new Error();
        eventos.push(evento);
      } catch {
        throw new Error(`Evento inválido em ${arquivo}, linha ${indice + 1}.`);
      }
    }
  }
  return eventos.sort((a, b) => Date.parse(a.horaParede) - Date.parse(b.horaParede)
    || a.horaParede.localeCompare(b.horaParede));
}

function imprimirHistorico(eventos) {
  console.log('=== Histórico de eventos de eleição ===');
  for (const evento of eventos) {
    console.log(`(${evento.horaParede}) [${evento.agencia}] ${evento.tipo}`,
      JSON.stringify(evento.detalhes));
  }
  console.log('\n=== Linha do tempo de líderes declaradas ===');
  const liderancas = eventos.filter((evento) => evento.tipo === 'TORNOU_LIDER');
  if (!liderancas.length) console.log('Nenhuma declaração de liderança nos logs.');
  for (const evento of liderancas) {
    console.log(`${evento.horaParede} · Agência ${evento.detalhes.idAgencia} declarou liderança`);
  }
}

const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--dados')) {
  console.error('Uso: node agencia/historico-lideranca.js [--dados pasta]');
  process.exitCode = 1;
} else {
  try {
    const pasta = args[1] ?? path.join(__dirname, 'data');
    imprimirHistorico(carregarEventos(pasta));
  } catch (erro) {
    console.error(erro.message);
    process.exitCode = 1;
  }
}
