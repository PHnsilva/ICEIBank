import 'dart:convert';

import 'package:hive_ce_flutter/hive_ce_flutter.dart';
import 'package:uuid/uuid.dart';

import 'api.dart';

BigInt centavos(String valor) {
  final partes = valor.split('.');
  final fracao = partes.length == 2 ? partes[1].padRight(2, '0') : '00';
  return BigInt.parse('${partes.first}$fracao');
}

String moeda(BigInt valor) {
  final digitos = valor.abs().toString().padLeft(3, '0');
  final sinal = valor.isNegative ? '-' : '';
  return '$sinal${digitos.substring(0, digitos.length - 2)},${digitos.substring(digitos.length - 2)}';
}

class Pendencia {
  Pendencia(
    this.id,
    this.tipo,
    this.valor,
    this.vetor,
    this.versao, {
    this.falha,
  });

  factory Pendencia.fromJson(Json dados) => Pendencia(
    dados['operacaoId'] as String,
    dados['tipo'] as String,
    dados['valor'] as String,
    (dados['vetorConhecido'] as List).cast<int>(),
    dados['versaoAgencia'] as String,
    falha: dados['falha'] as String?,
  );

  factory Pendencia.nova(String tipo, String valor, Json base) => Pendencia(
    const Uuid().v4(),
    tipo,
    valor,
    (base['vetorAtual'] as List).cast<int>(),
    base['versaoAgencia'] as String,
  );

  final String id;
  final String tipo;
  final String valor;
  final List<int> vetor;
  final String versao;
  final String? falha;

  Json get pedido => {
    'operacaoId': id,
    'tipo': tipo,
    'valor': valor,
    'vetorConhecido': vetor,
    'versaoAgencia': versao,
  };

  Json toJson() => {...pedido, 'falha': falha};

  BigInt get efeito => tipo == 'SAQUE' ? -centavos(valor) : centavos(valor);

  Pendencia comBase(Json conta) => Pendencia(
    id,
    tipo,
    valor,
    (conta['vetorAtual'] as List).cast<int>(),
    conta['versaoAgencia'] as String,
  );

  Pendencia rejeitada(String motivo) =>
      Pendencia(id, tipo, valor, vetor, versao, falha: motivo);
}

class ContaLocal {
  ContaLocal(this.confirmada, this.operacoes);

  factory ContaLocal.fromJson(Json dados) => ContaLocal(
    dados['confirmada'] as Json?,
    (dados['operacoes'] as List).cast<Json>().map(Pendencia.fromJson).toList(),
  );

  final Json? confirmada;
  final List<Pendencia> operacoes;

  Iterable<Pendencia> get pendentes =>
      operacoes.where((item) => item.falha == null);
  BigInt? get saldoConfirmado =>
      confirmada == null ? null : centavos(confirmada!['saldo'] as String);
  BigInt? get saldoProvisorio => saldoConfirmado == null
      ? null
      : pendentes.fold<BigInt>(
          saldoConfirmado!,
          (saldo, item) => saldo + item.efeito,
        );

  Json toJson() => {
    'confirmada': confirmada,
    'operacoes': operacoes.map((item) => item.toJson()).toList(),
  };
}

class BancoLocal {
  BancoLocal(this.caixa, String host, String usuario)
    : prefixo = '${jsonEncode([host, usuario])}:';

  final Box<String> caixa;
  final String prefixo;

  ContaLocal ler(int id) {
    final dados = caixa.get('$prefixo$id');
    return dados == null
        ? ContaLocal(null, [])
        : ContaLocal.fromJson(jsonDecode(dados) as Json);
  }

  Map<int, ContaLocal> lerTodas() => {
    for (final chave in caixa.keys.whereType<String>())
      if (chave.startsWith(prefixo))
        int.parse(chave.substring(prefixo.length)): ler(
          int.parse(chave.substring(prefixo.length)),
        ),
  };

  // O saldo e a fila da conta são gravados juntos em uma única entrada.
  Future<void> gravar(int id, ContaLocal conta) =>
      caixa.put('$prefixo$id', jsonEncode(conta.toJson()));

  Future<void> dispensarFalhas(int id) {
    final conta = ler(id);
    return gravar(id, ContaLocal(conta.confirmada, conta.pendentes.toList()));
  }
}

class Sincronizacao {
  Sincronizacao(this.api, this.banco);

  final IceiBankApi api;
  final BancoLocal banco;

  Future<bool> consultar(int id) async {
    final local = banco.ler(id);
    // Com uma resposta incerta, resolva a repetição idempotente antes de
    // atualizar a base sobre a qual a projeção está sendo exibida.
    if (local.pendentes.isNotEmpty) return false;
    try {
      final atual = await api.saldo(id);
      await banco.gravar(id, ContaLocal(atual, local.operacoes));
      return true;
    } on ApiException catch (erro) {
      if (erro.indisponivel && local.confirmada != null) return false;
      if (erro.status == 404 && local.confirmada != null) {
        await banco.gravar(id, ContaLocal(null, local.operacoes));
      }
      rethrow;
    }
  }

  Future<bool> registrar(int id, String tipo, String valor) async {
    if (centavos(valor) <= BigInt.zero || valor.split('.').first.length > 14) {
      throw const ApiException(
        'Informe um valor positivo de até 14 dígitos inteiros.',
      );
    }
    final bool conectado;
    try {
      conectado = await consultar(id);
    } on ApiException catch (erro) {
      if (!erro.indisponivel) rethrow;
      throw const ApiException(
        'Consulte o saldo desta conta online antes de operar offline.',
      );
    }

    final local = banco.ler(id);
    final novo = Pendencia.nova(tipo, valor, local.confirmada!);
    if (local.saldoProvisorio! + novo.efeito < BigInt.zero) {
      throw const ApiException(
        'Saldo disponível insuficiente para realizar o saque.',
      );
    }
    await banco.gravar(
      id,
      ContaLocal(local.confirmada, [...local.operacoes, novo]),
    );
    if (conectado) await sincronizarConta(id);
    return !banco.ler(id).operacoes.any((item) => item.id == novo.id);
  }

  Future<void> sincronizarConta(int id) async {
    var local = banco.ler(id);
    while (local.pendentes.isNotEmpty) {
      final item = local.pendentes.first;
      final Json atual;
      try {
        atual = await api.sincronizar(id, item.pedido);
      } on ApiException catch (erro) {
        final status = erro.status;
        if (erro.indisponivel || status == null || status < 400) return;
        if (status == 401) rethrow;
        final confirmada = erro.dados?['contaAtual'] as Json?;
        final motivo = status == 409
            ? 'Conflito de sincronização. Revise a operação.'
            : erro.message;
        await banco.gravar(
          id,
          ContaLocal(
            confirmada,
            local.operacoes
                .map((op) => op.falha == null ? op.rejeitada(motivo) : op)
                .toList(),
          ),
        );
        return;
      }
      // As próximas operações da mesma conta podem partir do resultado desta
      // operação. O servidor ainda compara o vetor com o estado real a cada POST.
      local = ContaLocal(atual, [
        for (final op in local.operacoes)
          if (op.id != item.id) op.falha == null ? op.comBase(atual) : op,
      ]);
      await banco.gravar(id, local);
    }
  }
}
