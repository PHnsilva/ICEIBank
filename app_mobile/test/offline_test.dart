import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce_flutter/hive_ce_flutter.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:iceibank_mobile/api.dart';
import 'package:iceibank_mobile/offline.dart';

void main() {
  const id = 3;
  const versao = '22222222-2222-4222-8222-222222222222';
  late Directory pasta;
  late Box<String> caixa;

  Json conta(String saldo, int versaoLocal) => {
    'id': id,
    'nomeAluno': 'Ana',
    'saldo': saldo,
    'vetorAtual': [versaoLocal, 0, 0],
    'versaoAgencia': versao,
  };

  http.Response resposta(Json corpo, [int status = 200]) =>
      http.Response(jsonEncode(corpo), status);

  setUp(() async {
    pasta = await Directory.systemTemp.createTemp('iceibank_hive_');
    Hive.init(pasta.path);
    caixa = await Hive.openBox<String>('contas');
  });

  tearDown(() async {
    await caixa.close();
    await pasta.delete(recursive: true);
  });

  test(
    'fila e projeção sobrevivem ao fechamento e a sincronização é ordenada',
    () async {
      var offline = false;
      final pedidos = <Json>[];
      final api = IceiBankApi(
        '127.0.0.1',
        client: MockClient((request) async {
          if (offline) throw http.ClientException('Sem rede');
          if (request.method == 'GET') return resposta(conta('100.00', 1));
          pedidos.add(jsonDecode(request.body) as Json);
          return pedidos.length == 1
              ? resposta(conta('110.25', 2))
              : resposta(conta('90.25', 3));
        }),
      );
      addTearDown(api.fechar);

      var local = BancoLocal(caixa, api.host, 'aluno');
      var sync = Sincronizacao(api, local);
      expect(await sync.consultar(id), isTrue);
      offline = true;
      await sync.registrar(id, 'DEPOSITO', '10.25');
      await sync.registrar(id, 'SAQUE', '20.00');

      await caixa.close();
      caixa = await Hive.openBox<String>('contas');
      local = BancoLocal(caixa, api.host, 'aluno');
      sync = Sincronizacao(api, local);
      expect(local.ler(id).saldoConfirmado, BigInt.from(10000));
      expect(local.ler(id).saldoProvisorio, BigInt.from(9025));
      expect(BancoLocal(caixa, api.host, 'outro').lerTodas(), isEmpty);

      offline = false;
      await sync.sincronizarConta(id);
      expect(pedidos.map((pedido) => pedido['tipo']), ['DEPOSITO', 'SAQUE']);
      expect(pedidos.map((pedido) => pedido['vetorConhecido']), [
        [1, 0, 0],
        [2, 0, 0],
      ]);
      expect(local.ler(id).operacoes, isEmpty);
      expect(local.ler(id).saldoConfirmado, BigInt.from(9025));
    },
  );

  test(
    '409 remove a projeção, mostra saldo real e preserva os avisos',
    () async {
      var offline = false;
      var envios = 0;
      final api = IceiBankApi(
        '127.0.0.1',
        client: MockClient((request) async {
          if (offline) throw http.ClientException('Sem rede');
          if (request.method == 'GET') return resposta(conta('100.00', 1));
          envios++;
          return resposta({
            'detail': 'Conflito',
            'contaAtual': conta('110.00', 2),
          }, 409);
        }),
      );
      addTearDown(api.fechar);

      final local = BancoLocal(caixa, api.host, 'aluno');
      final sync = Sincronizacao(api, local);
      await sync.consultar(id);
      offline = true;
      await sync.registrar(id, 'SAQUE', '10.00');
      await sync.registrar(id, 'DEPOSITO', '1.00');
      offline = false;
      await sync.sincronizarConta(id);
      await sync.sincronizarConta(id);

      final estado = local.ler(id);
      expect(envios, 1);
      expect(estado.saldoConfirmado, BigInt.from(11000));
      expect(estado.saldoProvisorio, estado.saldoConfirmado);
      expect(estado.pendentes, isEmpty);
      expect(estado.operacoes, hasLength(2));
      expect(
        estado.operacoes.map((item) => item.falha),
        everyElement(contains('Conflito')),
      );
    },
  );
}
