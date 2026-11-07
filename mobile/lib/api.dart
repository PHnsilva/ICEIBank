import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

typedef Json = Map<String, dynamic>;

class ApiException implements Exception {
  const ApiException(this.message, {this.status});

  final String message;
  final int? status;
}

class IceiBankApi {
  IceiBankApi(this.host, {http.Client? client})
    : _client = client ?? http.Client();

  final String host;
  final http.Client _client;
  String? _token;
  static const agencias = [0, 1, 2];

  bool get autenticado => _token != null;

  void sair() => _token = null;

  void fechar() => _client.close();

  Future<Json> _enviar(
    int agencia,
    String caminho, {
    Json? corpo,
    bool publico = false,
  }) async {
    final uri = Uri(
      scheme: 'http',
      host: host,
      port: 4078 + agencia,
      path: caminho,
    );
    final headers = {
      if (corpo != null) 'Content-Type': 'application/json',
      if (!publico && _token != null) 'Authorization': 'Bearer $_token',
    };
    final http.Response resposta;
    try {
      final pedido = corpo == null
          ? _client.get(uri, headers: headers)
          : _client.post(uri, headers: headers, body: jsonEncode(corpo));
      resposta = await pedido.timeout(const Duration(seconds: 3));
    } on Exception catch (erro) {
      if (erro is! TimeoutException && erro is! http.ClientException) rethrow;
      final aviso = corpo != null && !publico
          ? ' Confira o saldo e o histórico antes de repetir a operação.'
          : '';
      throw ApiException('Agência $agencia sem resposta.$aviso');
    }
    if (resposta.statusCode == 401 && !publico) sair();
    final Object? dados;
    try {
      dados = jsonDecode(utf8.decode(resposta.bodyBytes));
    } on FormatException {
      throw ApiException(
        'Resposta inválida da agência $agencia.',
        status: resposta.statusCode,
      );
    }
    if (resposta.statusCode < 200 || resposta.statusCode >= 300) {
      final detail = dados is Json ? dados['detail'] : null;
      throw ApiException(
        detail is String ? detail : 'Erro HTTP ${resposta.statusCode}.',
        status: resposta.statusCode,
      );
    }
    if (dados is! Json) throw const ApiException('Resposta inesperada.');
    return dados;
  }

  Future<void> entrar(String usuario, String senha, {int? lider}) async {
    final ordem = [?lider, ...agencias.where((id) => id != lider)];
    for (final agencia in ordem) {
      try {
        final dados = await _enviar(
          agencia,
          '/auth/login',
          corpo: {'usuario': usuario, 'senha': senha},
          publico: true,
        );
        final token = dados['access_token'];
        if (token is! String || token.isEmpty) {
          throw const ApiException('Token de login inválido.');
        }
        _token = token;
        return;
      } on ApiException catch (erro) {
        if (erro.status != null && erro.status! < 500) rethrow;
      }
    }
    throw const ApiException('Nenhuma agência disponível para login.');
  }

  Future<List<Json?>> statusCluster() => Future.wait(
    agencias.map((id) async {
      try {
        final dados = await _enviar(id, '/cluster/status', publico: true);
        return dados['agenciaId'] == id ? dados : null;
      } on ApiException {
        return null;
      }
    }),
  );

  Future<Json> saldo(int id) => _enviar(id % 3, '/contas/$id');

  Future<Json> historico(int id) => _enviar(id % 3, '/contas/$id/historico');

  Future<Json> criar(int id, String nome, String saldo) => _enviar(
    id % 3,
    '/contas',
    corpo: {'id': id, 'nomeAluno': nome, 'saldoInicial': saldo},
  );

  Future<Json> movimentar(int id, String operacao, String valor) =>
      _enviar(id % 3, '/contas/$id/$operacao', corpo: {'valor': valor});

  Future<Json> transferir(int origem, int destino, String valor) => _enviar(
    origem % 3,
    '/transferencias',
    corpo: {'idOrigem': origem, 'idDestino': destino, 'valor': valor},
  );
}
