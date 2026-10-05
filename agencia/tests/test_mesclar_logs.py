import json

import pytest

from agencia.mesclar_logs import carregar_eventos, imprimir_linha_do_tempo, pares_concorrentes


def evento(agencia, vetor, tipo="CRIAR_CONTA", hora="2026-10-04T12:00:00Z"):
    return {"agencia": agencia, "timestampVetorial": vetor, "tipo": tipo, "horaParede": hora, "detalhes": {}}


def test_concorrencia_e_causalidade_do_roteiro(capsys):
    a = evento("agencia-0", [1, 0, 0])
    b = evento("agencia-1", [0, 1, 0])
    debito = evento("agencia-0", [2, 0, 0], "TRANSFERENCIA_DEBITO")
    credito = evento("agencia-1", [3, 2, 0], "TRANSFERENCIA_CREDITO_REMOTO")
    eventos = [a, b, debito, credito]
    pares = list(pares_concorrentes(eventos))
    assert (a, b) in pares
    assert (debito, credito) not in pares
    assert (a, debito) not in pares
    imprimir_linha_do_tempo(eventos)
    saida = capsys.readouterr().out
    assert "CONCORRENTES" in saida
    assert "vetor=[3, 2, 0]" in saida


def test_ordena_por_parede_e_exclui_lamport_legado(tmp_path, capsys):
    a = evento("agencia-0", [2, 0, 0], hora="2026-10-04T12:00:00Z")
    b = evento("agencia-1", [0, 9, 0], hora="2026-10-04T11:00:00Z")
    legado = {"timestampLamport": 1}
    (tmp_path / "eventos.jsonl").write_text("\n" + "\n".join(map(json.dumps, [a, b, legado])), encoding="utf-8")
    assert carregar_eventos(tmp_path) == [b, a]
    assert "1 eventos Lamport" in capsys.readouterr().out


@pytest.mark.parametrize("texto", ['{quebrado}', '{"timestampVetorial": [1, 2]}'])
def test_erro_tem_arquivo_e_linha(tmp_path, texto):
    (tmp_path / "eventos-agencia-0.jsonl").write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match="eventos-agencia-0.jsonl, linha 1"):
        carregar_eventos(tmp_path)


def test_logs_vazios_nao_inventam_concorrencia(capsys):
    imprimir_linha_do_tempo([])
    assert "nenhum par concorrente" in capsys.readouterr().out
