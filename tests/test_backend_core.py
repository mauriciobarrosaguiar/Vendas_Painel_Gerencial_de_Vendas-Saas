from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.core import calculos as core_calculos
from backend.core import filtros_core
from backend.core import loader_core
from backend.core import mercado_farma as core_mf


def test_backend_core_has_no_streamlit_or_src_imports() -> None:
    core_dir = Path(__file__).resolve().parents[1] / "backend" / "core"
    for path in core_dir.glob("*.py"):
        texto = path.read_text(encoding="utf-8")
        assert "streamlit" not in texto.lower(), path
        assert "from src" not in texto, path
        assert "import src" not in texto, path


def test_backend_loader_core_matches_local_baseline(real_data_paths: dict[str, Path]) -> None:
    if any(not path.exists() for path in real_data_paths.values()):
        pytest.skip("Bases reais locais nao disponiveis.")

    dados = loader_core.carregar_dados_tratados_de_arquivos(Path(__file__).resolve().parents[1])
    vendas = dados["vendas"]
    clientes = dados["clientes"]
    assert isinstance(vendas, pd.DataFrame)
    assert isinstance(clientes, pd.DataFrame)

    assert vendas.shape == (11952, 54)
    assert clientes.shape == (543, 55)

    indicadores = core_calculos.calcular_indicadores(vendas, clientes)
    resumo = core_calculos.calcular_resumo_operacional(vendas, clientes)

    assert indicadores["ol_sem_combate"] == pytest.approx(511082.95)
    assert indicadores["quantidade_pedidos"] == 1094
    assert indicadores["clientes_positivados"] == 62
    assert resumo["pedidos_sem_nota"] == 26
    assert resumo["valor_sem_nota"] == pytest.approx(11394.19)


def test_filtros_core(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    filtros = {
        "inicio": "2026-05-01",
        "fim": "2026-05-31",
        "consultor": ["Ana"],
        "status_modo": "Apenas faturados",
    }
    vendas_f, clientes_f, filtros_norm = filtros_core.aplicar_filtros_globais_core(vendas, clientes, filtros)

    assert filtros_norm["restringir_por_clientes"] is True
    assert set(clientes_f["nome_rep"]) == {"Ana"}
    assert set(vendas_f["consultor"]) == {"Ana"}
    assert set(vendas_f["status_normalizado"]) == {"FATURADO", "FATURADO PARCIAL"}

    opcoes = filtros_core.calcular_opcoes_filtros(vendas, clientes)
    assert "Ana" in opcoes["consultores"]
    assert "Bruno" in opcoes["consultores"]
    assert opcoes["meses"] == ["2026-05"]


def test_mercado_farma_core() -> None:
    raw = pd.DataFrame(
        [
            {
                "UF": "MA",
                "CNPJ_REFERENCIA": "12.345.678/0001-90",
                "EAN": "789123",
                "PRODUTO": "Produto A",
                "DISTRIBUIDORA": "Dist 1",
                "ESTOQUE": "5",
                "DESCONTO": "10",
                "PF_DIST": "100",
                "PF_FABRICA": "110",
                "PRECO_COM_IMPOSTO": "90",
                "PRECO_SEM_IMPOSTO": "80",
                "STATUS": "OK",
            },
            {
                "UF": "MA",
                "CNPJ_REFERENCIA": "12.345.678/0001-90",
                "EAN": "789123",
                "PRODUTO": "Produto A",
                "DISTRIBUIDORA": "Dist 2",
                "ESTOQUE": "8",
                "DESCONTO": "5",
                "PF_DIST": "100",
                "PF_FABRICA": "110",
                "PRECO_COM_IMPOSTO": "85",
                "PRECO_SEM_IMPOSTO": "70",
                "STATUS": "OK",
            },
        ]
    )

    mercado = core_mf.preparar_mercado_farma(raw)
    assert mercado["cnpj_referencia"].iloc[0] == "12345678000190"
    assert mercado["desconto"].iloc[0] == 0.10

    melhores = core_mf.melhor_preco_por_ean(mercado)
    assert len(melhores) == 1
    assert melhores.iloc[0]["distribuidora"] == "Dist 2"

    com_desconto = core_mf.aplicar_descontos_adicionais(
        mercado,
        {"distribuidoras": {"Dist 2": {"percentual": 0.1, "eans_sem_desconto": []}}},
    )
    assert com_desconto.loc[com_desconto["distribuidora"].eq("Dist 2"), "preco_sem_imposto"].iloc[0] == 63

