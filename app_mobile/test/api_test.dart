import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:iceibank_mobile/api.dart';

void main() {
  test(
    'login alterna agência e transferência usa a partição de origem',
    () async {
      final portas = <int>[];
      final api = IceiBankApi(
        '10.0.2.2',
        client: MockClient((pedido) async {
          portas.add(pedido.url.port);
          if (pedido.url.path == '/auth/login') {
            if (pedido.url.port == 4080) throw http.ClientException('Offline');
            return http.Response('{"access_token":"teste"}', 200);
          }
          expect(pedido.method, 'POST');
          expect(pedido.url.path, '/transferencias');
          expect(pedido.headers['Authorization'], 'Bearer teste');
          expect(jsonDecode(pedido.body), {
            'idOrigem': 4,
            'idDestino': 5,
            'valor': '10.50',
          });
          return http.Response('{"status":"publicada"}', 200);
        }),
      );
      addTearDown(api.fechar);
      await api.entrar('aluno', 'senha', lider: 2);
      expect((await api.transferir(4, 5, '10.50'))['status'], 'publicada');
      expect(portas, [4080, 4078, 4079]);
    },
  );

  test(
    'uma mutação sem resposta é enviada uma vez e 401 limpa a sessão',
    () async {
      var envios = 0;
      final api = IceiBankApi(
        '10.0.2.2',
        client: MockClient((pedido) async {
          if (pedido.url.path == '/auth/login') {
            return http.Response('{"access_token":"teste"}', 200);
          }
          if (pedido.method == 'POST') {
            envios++;
            throw http.ClientException('Offline');
          }
          return http.Response('{"detail":"Sessão expirada."}', 401);
        }),
      );
      addTearDown(api.fechar);
      await api.entrar('aluno', 'senha');
      await expectLater(
        api.movimentar(1, 'depositar', '1.00'),
        throwsA(isA<ApiException>()),
      );
      expect(envios, 1);
      await expectLater(api.saldo(1), throwsA(isA<ApiException>()));
      expect(api.autenticado, isFalse);
    },
  );
}
