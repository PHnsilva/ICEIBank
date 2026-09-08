"""Testes do mesclador da linha do tempo de Lamport."""

import json
from pathlib import Path

import pytest

from agencia.mesclar_logs import CABECALHO, carregar_eventos, imprimir_linha_do_tempo


def _evento(agencia: str, timestamp: int, hora: str, tipo: str) -> dict[str, object]:
    return {
        "agencia": agencia,
        "tipo": tipo,
        "timestampLamport": timestamp,
        "horaParede": hora,
        "detalhes": {"teste": tipo},
    }


def test_le_todos_os_jsonl_ignora_linhas_vazias_e_ordena(tmp_path: Path) -> None:
    evento_l2 = _evento("agencia-0", 2, "2026-01-01T00:00:03Z", "DEPOSITO")
    evento_l1_tarde = _evento("agencia-1", 1, "2026-01-01T00:00:02Z", "CRIAR_CONTA")
    evento_l1_cedo = _evento("agencia-2", 1, "2026-01-01T00:00:01Z", "CRIAR_CONTA")
    (tmp_path / "eventos-agencia-0.jsonl").write_text(
        f"{json.dumps(evento_l2)}\n\n{json.dumps(evento_l1_tarde)}\n",
        encoding="utf-8",
    )
    (tmp_path / "eventos-agencia-2.jsonl").write_text(
        f"\n{json.dumps(evento_l1_cedo)}\n",
        encoding="utf-8",
    )
    (tmp_path / "ignorar.txt").write_text("não é um log", encoding="utf-8")

    eventos = carregar_eventos(tmp_path)

    assert [evento["timestampLamport"] for evento in eventos] == [1, 1, 2]
    assert [evento["agencia"] for evento in eventos[:2]] == ["agencia-2", "agencia-1"]


def test_impressao_mostra_campos_detalhes_e_empate(capsys: pytest.CaptureFixture[str]) -> None:
    eventos = [
        _evento("agencia-0", 1, "2026-01-01T00:00:01Z", "CRIAR_CONTA"),
        _evento("agencia-1", 1, "2026-01-01T00:00:02Z", "CRIAR_CONTA"),
        _evento("agencia-0", 2, "2026-01-01T00:00:03Z", "DEPOSITO"),
    ]

    imprimir_linha_do_tempo(eventos)

    saida = capsys.readouterr().out
    assert CABECALHO in saida
    assert saida.count("[EMPATE x2]") == 2
    assert "L=0002 |" in saida
    assert "parede=2026-01-01T00:00:01Z" in saida
    assert "agencia=agencia-0" in saida
    assert "tipo=CRIAR_CONTA" in saida
    assert 'detalhes={"teste": "CRIAR_CONTA"}' in saida


def test_rejeita_linha_json_invalida_com_localizacao(tmp_path: Path) -> None:
    (tmp_path / "eventos-agencia-0.jsonl").write_text("{quebrado}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="eventos-agencia-0.jsonl, linha 1"):
        carregar_eventos(tmp_path)


def test_informa_quando_nao_ha_eventos(capsys: pytest.CaptureFixture[str]) -> None:
    imprimir_linha_do_tempo([])

    saida = capsys.readouterr().out
    assert CABECALHO in saida
    assert "Nenhum evento foi encontrado" in saida
