# ICEIBank para Android

Cliente Flutter para acompanhar a eleição, autenticar com JWT, criar contas
e consultar saldo e histórico. Também permite depositar, sacar e transferir.

## Executar no emulador Android

Use Flutter estável com Dart 3.13.7 ou superior, Android SDK e um emulador
disponível em `flutter devices`. Inicie o RabbitMQ e as três agências
conforme o [guia da Sprint 3](../docs/Sprint3.md).

Da pasta `mobile`, execute:

```sh
flutter pub get
flutter run --debug
```

O emulador usa `10.0.2.2` para acessar as portas 4078 a 4080 do computador.
O modo debug permite HTTP para esta demonstração local. Para informar outro
endereço alcançável pelo Android, passe `--dart-define=ICEIBANK_HOST=<host>`.

O painel atualiza o estado das três agências periodicamente. O login tenta
a líder primeiro quando conhecida, e o JWT fica em memória. Operações de
conta são enviadas à agência responsável e, se houver falha de comunicação,
o app apresenta o erro sem repetir a movimentação.

## Verificação do cliente

```sh
flutter analyze
flutter test
```
