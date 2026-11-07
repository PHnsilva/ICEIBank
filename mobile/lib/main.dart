import 'dart:async';

import 'package:flutter/material.dart';

import 'api.dart';

void main() => runApp(const IceiBankApp());

class IceiBankApp extends StatelessWidget {
  const IceiBankApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ICEIBank',
    theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal)),
    home: const PainelBancario(),
  );
}

enum Operacao {
  saldo('Consultar saldo'),
  historico('Consultar histórico'),
  criar('Criar conta'),
  depositar('Depositar'),
  sacar('Sacar'),
  transferir('Transferir');

  const Operacao(this.rotulo);
  final String rotulo;

  bool get usaValor => switch (this) {
    saldo || historico => false,
    _ => true,
  };
}

class PainelBancario extends StatefulWidget {
  const PainelBancario({super.key});

  @override
  State<PainelBancario> createState() => _PainelBancarioState();
}

class _PainelBancarioState extends State<PainelBancario> {
  final api = IceiBankApi(
    const String.fromEnvironment('ICEIBANK_HOST', defaultValue: '10.0.2.2'),
  );
  final usuario = TextEditingController();
  final senha = TextEditingController();
  final conta = TextEditingController();
  final destino = TextEditingController();
  final nome = TextEditingController();
  final valor = TextEditingController();
  late final Timer timer;
  List<Json?> agencias = [null, null, null];
  Operacao operacao = Operacao.saldo;
  String mensagem = '';
  List<String> eventos = [];
  bool erro = false;
  bool ocupado = false;
  bool consultandoCluster = false;

  Json? get lider {
    final lideres = agencias
        .whereType<Json>()
        .where(
          (agencia) =>
              agencia['papel'] == 'lider' &&
              agencia['agenciaId'] == agencia['liderId'],
        )
        .toList();
    return lideres.length == 1 ? lideres.single : null;
  }

  @override
  void initState() {
    super.initState();
    unawaited(atualizarCluster());
    timer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(atualizarCluster());
    });
  }

  @override
  void dispose() {
    timer.cancel();
    api.fechar();
    for (final campo in [usuario, senha, conta, destino, nome, valor]) {
      campo.dispose();
    }
    super.dispose();
  }

  Future<void> atualizarCluster() async {
    if (consultandoCluster) return;
    consultandoCluster = true;
    try {
      final status = await api.statusCluster();
      if (mounted) setState(() => agencias = status);
    } finally {
      consultandoCluster = false;
    }
  }

  Future<void> executar(Future<String> Function() acao) async {
    setState(() {
      ocupado = true;
      erro = false;
      mensagem = '';
      eventos = [];
    });
    try {
      final resposta = await acao();
      if (mounted) setState(() => mensagem = resposta);
    } on ApiException catch (falha) {
      if (mounted) {
        setState(() {
          erro = true;
          mensagem = falha.message;
        });
      }
    } finally {
      if (mounted) setState(() => ocupado = false);
    }
  }

  Future<String> entrar() async {
    if (usuario.text.trim().isEmpty || senha.text.isEmpty) {
      throw const ApiException('Informe usuário e senha.');
    }
    await api.entrar(
      usuario.text.trim(),
      senha.text,
      lider: lider?['agenciaId'] as int?,
    );
    if (mounted) senha.clear();
    return 'Sessão iniciada.';
  }

  int lerConta(TextEditingController campo) {
    final texto = campo.text.trim();
    final id = int.tryParse(texto);
    if (!RegExp(r'^[0-9]+$').hasMatch(texto) || id == null) {
      throw const ApiException(
        'Informe um número de conta inteiro e não negativo.',
      );
    }
    return id;
  }

  Future<String> enviarOperacao() async {
    final id = lerConta(conta);
    final quantia = valor.text.trim().replaceAll(',', '.');
    if (operacao.usaValor &&
        !RegExp(r'^[0-9]+(\.[0-9]{1,2})?$').hasMatch(quantia)) {
      throw const ApiException('Informe um valor com até duas casas decimais.');
    }
    switch (operacao) {
      case Operacao.saldo:
        final dados = await api.saldo(id);
        return 'Conta $id · Saldo R\$ ${dados['saldo']}';
      case Operacao.historico:
        final dados = await api.historico(id);
        final itens = (dados['eventos'] as List).whereType<Json>();
        if (mounted) {
          setState(
            () => eventos = itens
                .map((item) => "${item['tipo']} · ${item['horaParede']}")
                .toList(),
          );
        }
        return 'Conta $id · ${itens.length} evento(s) exibido(s)';
      case Operacao.criar:
        if (nome.text.trim().isEmpty) {
          throw const ApiException('Informe o nome.');
        }
        final dados = await api.criar(id, nome.text.trim(), quantia);
        return 'Conta $id criada · Saldo R\$ ${dados['saldo']}';
      case Operacao.depositar || Operacao.sacar:
        final dados = await api.movimentar(id, operacao.name, quantia);
        return 'Operação concluída · Saldo R\$ ${dados['saldo']}';
      case Operacao.transferir:
        final dados = await api.transferir(id, lerConta(destino), quantia);
        return dados['status'] == 'publicada'
            ? 'Transferência publicada. Consulte a conta de destino para confirmar o crédito.'
            : 'Transferência concluída · Saldo de origem R\$ ${dados['saldoOrigem']}';
    }
  }

  Widget campo(
    TextEditingController controller,
    String rotulo, {
    bool segredo = false,
    TextInputType? teclado,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      controller: controller,
      enabled: !ocupado,
      obscureText: segredo,
      keyboardType: teclado,
      decoration: InputDecoration(labelText: rotulo),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final atual = lider;
    return Scaffold(
      appBar: AppBar(
        title: const Text('ICEIBank'),
        actions: [
          if (api.autenticado)
            TextButton(
              onPressed: ocupado
                  ? null
                  : () => setState(() {
                      api.sair();
                      for (final campo in [conta, destino, nome, valor]) {
                        campo.clear();
                      }
                      mensagem = '';
                      eventos = [];
                    }),
              child: const Text('Sair'),
            ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      atual == null
                          ? 'Líder indisponível'
                          : "Agência ${atual['agenciaId']} lidera · Mandato ${atual['mandato']}",
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    for (final id in IceiBankApi.agencias)
                      Text(
                        'Agência $id · ${agencias[id]?['papel'] ?? 'sem resposta'}',
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (!api.autenticado) ...[
              campo(usuario, 'Usuário'),
              campo(senha, 'Senha', segredo: true),
              FilledButton(
                onPressed: ocupado ? null : () => executar(entrar),
                child: const Text('Entrar'),
              ),
            ] else ...[
              DropdownButtonFormField<Operacao>(
                initialValue: operacao,
                decoration: const InputDecoration(labelText: 'Operação'),
                items: Operacao.values
                    .map(
                      (item) => DropdownMenuItem(
                        value: item,
                        child: Text(item.rotulo),
                      ),
                    )
                    .toList(),
                onChanged: ocupado
                    ? null
                    : (item) {
                        if (item != null) {
                          setState(() {
                            operacao = item;
                            mensagem = '';
                            eventos = [];
                          });
                        }
                      },
              ),
              campo(conta, 'Número da conta', teclado: TextInputType.number),
              if (operacao == Operacao.criar) campo(nome, 'Nome'),
              if (operacao == Operacao.transferir)
                campo(
                  destino,
                  'Conta de destino',
                  teclado: TextInputType.number,
                ),
              if (operacao.usaValor)
                campo(
                  valor,
                  operacao == Operacao.criar ? 'Saldo inicial' : 'Valor',
                  teclado: const TextInputType.numberWithOptions(decimal: true),
                ),
              FilledButton(
                onPressed: ocupado ? null : () => executar(enviarOperacao),
                child: Text(operacao.rotulo),
              ),
            ],
            if (ocupado) const LinearProgressIndicator(),
            if (mensagem.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Semantics(
                  liveRegion: true,
                  child: Text(
                    mensagem,
                    style: TextStyle(
                      color: erro ? Theme.of(context).colorScheme.error : null,
                    ),
                  ),
                ),
              ),
            for (final evento in eventos) ListTile(title: Text(evento)),
          ],
        ),
      ),
    );
  }
}
