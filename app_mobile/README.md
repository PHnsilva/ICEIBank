# ICEIBank para Android

O [README principal](../README.md#7-sprint-3--executar-o-app-de-celular) traz a
instalação Linux, os passos no emulador/USB e o roteiro completo de apresentação.

## Alternativa Flutter Web

Com as três agências da `main` iniciadas, execute nesta pasta:

```bash
flutter pub get
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=8080 \
  --dart-define=ICEIBANK_HOST=localhost
```

Abra http://127.0.0.1:8080 na mesma máquina. As agências permitem essa origem
local na porta 8080. Para demonstrar a rede indisponível, mantenha a página
carregada e use DevTools → Network → Offline; depois retorne a Online.
Isso executa o cliente Flutter no navegador e não substitui a validação Android.

Cliente Flutter com login JWT, saldo, histórico, criação de conta, depósito,
saque, transferência local e entre agências. O painel consulta as três
agências e atualiza a líder e a disponibilidade automaticamente.

## Executar no emulador Android

Use Flutter com Dart 3.13.7 ou superior, Android SDK e um emulador em
`flutter devices`. Inicie o RabbitMQ e as três agências pelo
[guia da Sprint 3](../docs/Sprint3.md). Da pasta `app_mobile`:

```powershell
flutter pub get
flutter run --debug
```

O emulador usa `10.0.2.2` para acessar as portas 4078 a 4080 do computador.
O projeto permite HTTP no modo debug para a demonstração local. Em aparelho
via USB, com depuração habilitada, use `adb reverse` para cada porta e
informe `127.0.0.1` ao Flutter:

```powershell
4078..4080 | ForEach-Object { adb reverse "tcp:$_" "tcp:$_" }
flutter run --debug --dart-define=ICEIBANK_HOST=127.0.0.1
```

Para testar modo avião, use o emulador com o host padrão `10.0.2.2`. A
conexão USB de `adb reverse` pode continuar ativa quando o Wi-Fi é desligado.

## Demonstrar o fluxo offline

1. Entre e consulte uma conta para guardar o saldo confirmado e seu vetor.
2. Em modo avião, deposite ou saque na mesma conta. Observe a alteração
   provisória e o item pendente, ambos persistidos no Hive CE.
3. Reconecte com o app aberto. O saldo confirmado muda e o item sai da fila
   quando a agência aceita a operação.
4. Repita o passo 2 e, antes de reconectar, altere o saldo da conta por
   outro cliente. O app recebe o 409, retira a projeção do saldo e mostra
   a operação rejeitada junto do saldo retornado pela agência. Revise e, se
   ainda quiser fazer a operação, envie um novo pedido.

O JWT fica em memória. Ao fechar o app ou expirar a sessão, faça login
online no mesmo usuário para retomar o cache e a fila do dispositivo.

```powershell
flutter analyze
flutter test
```
