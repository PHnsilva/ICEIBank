"""Testes do formato do registro de eventos."""

import json
from datetime import datetime
from pathlib import Path

from agencia.app.services.registro_eventos import RegistroEventos


def test_registra_jsonl_em_utf8_com_campos_exatos(
    tmp_path: Path,
    capsys: object,
) -> None:
    registro = RegistroEventos(agencia_id=1, diretorio_dados=tmp_path / "dados")

    evento = registro.registrar(
        "EVENTO_TESTE",
        [0, 7, 0],
        {"nomeAluno": "João", "valor": "10.50"},
    )

    linhas = registro.caminho.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 1
    evento_gravado = json.loads(linhas[0])
    assert evento_gravado == evento
    assert set(evento_gravado) == {
        "agencia",
        "tipo",
        "timestampVetorial",
        "horaParede",
        "detalhes",
    }
    assert evento_gravado["agencia"] == "agencia-1"
    assert evento_gravado["tipo"] == "EVENTO_TESTE"
    assert evento_gravado["timestampVetorial"] == [0, 7, 0]
    assert evento_gravado["detalhes"]["nomeAluno"] == "João"
    assert datetime.fromisoformat(evento_gravado["horaParede"]).tzinfo is not None
    assert linhas[0] in capsys.readouterr().out  # type: ignore[attr-defined]


def test_acrescenta_um_objeto_por_linha(tmp_path: Path) -> None:
    registro = RegistroEventos(agencia_id=0, diretorio_dados=tmp_path)

    registro.registrar("PRIMEIRO", [1, 0, 0])
    registro.registrar("SEGUNDO", [2, 0, 0], {"ok": True})

    linhas = registro.caminho.read_text(encoding="utf-8").splitlines()
    assert [json.loads(linha)["tipo"] for linha in linhas] == ["PRIMEIRO", "SEGUNDO"]
