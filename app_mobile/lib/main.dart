import 'dart:async';

import 'package:flutter/material.dart';
import 'package:hive_ce_flutter/hive_ce_flutter.dart';

import 'api.dart';
import 'offline.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Hive.initFlutter();
    final caixa = await Hive.openBox<String>('iceibank_offline');
    runApp(IceiBankApp(caixa: caixa));
  } on Exception {
    runApp(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: Text(
              'Não foi possível abrir o armazenamento local do ICEIBank.',
            ),
          ),
        ),
      ),
    );
  }
}

class IceiBankApp extends StatelessWidget {
  const IceiBankApp({super.key, required this.caixa});

  final Box<String> caixa;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ICEIBank',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal)),
    home: PainelBancario(caixa: caixa),
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
  bool get usaValor => this != saldo && this != historico;
}

class PainelBancario extends StatefulWidget {
  const PainelBancario({super.key, required this.caixa});

  final Box<String> caixa;

  @override
  State<PainelBancario> createState() => _PainelBancarioState();
}

class _PainelBancarioState extends State<PainelBancario>
    with WidgetsBindingObserver {
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
  bool sincronizando = false;
  bool emPrimeiroPlano = true;
  Sincronizacao? offline;
  Map<int, ContaLocal> registros = {};

  bool get formularioBloqueado => ocupado || sincronizando;

  int? get lider {
    final ids = agencias
        .whereType<Json>()
        .map((agencia) => agencia['liderAtual'])
        .toSet();
    if (ids.length != 1) return null;
    final id = ids.single;
    if (id is! int ||
        !IceiBankApi.agencias.contains(id) ||
        agencias[id] == null) {
      return null;
    }
    return id;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(atualizarCluster());
    timer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(atualizarCluster());
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    timer.cancel();
    api.fechar();
    for (final campo in [usuario, senha, conta, destino, nome, valor]) {
      campo.dispose();
    }
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    emPrimeiroPlano = estado == AppLifecycleState.resumed;
    if (emPrimeiroPlano) unawaited(atualizarCluster());
  }

  Future<void> atualizarCluster() async {
    if (consultandoCluster || !emPrimeiroPlano) return;
    consultandoCluster = true;
    try {
      final status = await api.statusCluster();
      if (!mounted) return;
      setState(() => agencias = status);
      await sincronizarPendentes();
    } finally {
      consultandoCluster = false;
    }
  }

  Future<void> sincronizarPendentes() async {
    final local = offline;
    if (local == null ||
        !api.autenticado ||
        formularioBloqueado ||
        !emPrimeiroPlano) {
      return;
    }
    final ids = registros.keys
        .where(
          (id) =>
              agencias[id % 3] != null && registros[id]!.pendentes.isNotEmpty,
        )
        .toList();
    if (ids.isEmpty) return;
    setState(() => sincronizando = true);
    try {
      for (final id in ids) {
        await local.sincronizarConta(id);
      }
      if (mounted) {
        final houveConfirmacao = ids.every(
          (id) => local.banco.ler(id).operacoes.isEmpty,
        );
        if (houveConfirmacao) {
          setState(() {
            erro = false;
            mensagem = 'Operações sincronizadas.';
          });
        }
      }
    } on ApiException catch (falha) {
      mostrarErro(falha.message);
    } on Exception {
      mostrarErro('Não foi possível atualizar a fila local.');
    } finally {
      if (mounted) {
        setState(() {
          registros = local.banco.lerTodas();
          sincronizando = false;
        });
      }
    }
  }

  void mostrarErro(String aviso) {
    if (!mounted) return;
    setState(() {
      erro = true;
      mensagem = aviso;
    });
  }

  Future<void> executar(Future<String> Function() acao) async {
    if (formularioBloqueado) return;
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
      mostrarErro(falha.message);
    } on Exception {
      mostrarErro(
        'Não foi possível concluir a operação. Confira o estado da conta.',
      );
    } finally {
      if (mounted) {
        setState(() {
          registros = offline?.banco.lerTodas() ?? {};
          ocupado = false;
        });
      }
    }
  }

  Future<String> entrar() async {
    final nomeUsuario = usuario.text.trim();
    if (nomeUsuario.isEmpty || senha.text.isEmpty) {
      throw const ApiException('Informe usuário e senha.');
    }
    await api.entrar(nomeUsuario, senha.text, lider: lider);
    offline = Sincronizacao(
      api,
      BancoLocal(widget.caixa, api.host, nomeUsuario),
    );
    if (mounted) senha.clear();
    return 'Sessão iniciada.';
  }

  void sair() => setState(() {
    api.sair();
    offline = null;
    registros = {};
    for (final campo in [conta, destino, nome, valor]) {
      campo.clear();
    }
    mensagem = '';
    eventos = [];
  });

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
    final local = offline!;
    switch (operacao) {
      case Operacao.saldo:
        final atual = await local.consultar(id);
        return atual
            ? 'Saldo consultado.'
            : 'Exibindo o último saldo salvo no dispositivo.';
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
        final concluida = await local.registrar(
          id,
          operacao == Operacao.depositar ? 'DEPOSITO' : 'SAQUE',
          quantia,
        );
        return concluida ? 'Operação concluída.' : '';
      case Operacao.transferir:
        final dados = await api.transferir(id, lerConta(destino), quantia);
        if (local.banco.ler(id).pendentes.isEmpty) {
          // Uma transferência altera o saldo. Atualize a base quando possível
          // sem transformar uma falha de leitura em erro na transferência.
          try {
            await local.consultar(id);
          } on ApiException {
            // A mensagem abaixo continua descrevendo a resposta do POST.
          }
        }
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
      enabled: !formularioBloqueado,
      onChanged: controller == conta ? (_) => setState(() {}) : null,
      obscureText: segredo,
      keyboardType: teclado,
      decoration: InputDecoration(labelText: rotulo),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final atual = lider;
    final idConta = int.tryParse(conta.text.trim());
    final selecionada = registros[idConta];
    final tema = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('ICEIBank'),
        actions: [
          if (api.autenticado)
            TextButton(
              onPressed: formularioBloqueado ? null : sair,
              child: const Text('Sair'),
            ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
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
                              : 'Agência $atual lidera',
                          style: tema.textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 12,
                          runSpacing: 4,
                          children: [
                            for (final id in IceiBankApi.agencias)
                              Text(
                                'Agência $id · ${agencias[id] == null ? 'sem resposta' : 'ativa'}',
                              ),
                          ],
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
                    onPressed: formularioBloqueado
                        ? null
                        : () => executar(entrar),
                    child: const Text('Entrar'),
                  ),
                ] else ...[
                  DropdownButtonFormField<Operacao>(
                    initialValue: operacao,
                    decoration: const InputDecoration(labelText: 'Operação'),
                    items: [
                      for (final item in Operacao.values)
                        DropdownMenuItem(value: item, child: Text(item.rotulo)),
                    ],
                    onChanged: formularioBloqueado
                        ? null
                        : (item) {
                            if (item == null) return;
                            setState(() {
                              operacao = item;
                              mensagem = '';
                              eventos = [];
                            });
                          },
                  ),
                  campo(
                    conta,
                    'Número da conta',
                    teclado: TextInputType.number,
                  ),
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
                      teclado: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                    ),
                  FilledButton(
                    onPressed: formularioBloqueado
                        ? null
                        : () => executar(enviarOperacao),
                    child: Text(operacao.rotulo),
                  ),
                  const SizedBox(height: 8),
                  if (selecionada != null &&
                      selecionada.saldoConfirmado != null)
                    Card(
                      child: ListTile(
                        title: Text(
                          'Saldo confirmado · R\$ ${moeda(selecionada.saldoConfirmado!)}',
                        ),
                        subtitle: selecionada.pendentes.isEmpty
                            ? null
                            : Text(
                                'Saldo provisório · R\$ ${moeda(selecionada.saldoProvisorio!)}',
                              ),
                      ),
                    ),
                  for (final entrada in registros.entries)
                    for (final item in entrada.value.operacoes)
                      ListTile(
                        leading: Icon(
                          item.falha == null
                              ? Icons.schedule
                              : Icons.error_outline,
                          color: item.falha == null
                              ? null
                              : tema.colorScheme.error,
                        ),
                        title: Text(
                          'Conta ${entrada.key} · ${item.tipo == 'SAQUE' ? 'Saque' : 'Depósito'} de R\$ ${moeda(centavos(item.valor))}',
                        ),
                        subtitle: Text(
                          item.falha ?? 'Pendente de sincronização',
                        ),
                      ),
                  if (idConta != null &&
                      (selecionada?.operacoes.any(
                            (item) => item.falha != null,
                          ) ??
                          false))
                    TextButton(
                      onPressed: formularioBloqueado
                          ? null
                          : () => executar(() async {
                              await offline!.banco.dispensarFalhas(idConta);
                              return '';
                            }),
                      child: const Text('Dispensar avisos desta conta'),
                    ),
                ],
                if (formularioBloqueado) const LinearProgressIndicator(),
                if (mensagem.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(
                        mensagem,
                        style: TextStyle(
                          color: erro ? tema.colorScheme.error : null,
                        ),
                      ),
                    ),
                  ),
                for (final evento in eventos) ListTile(title: Text(evento)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
