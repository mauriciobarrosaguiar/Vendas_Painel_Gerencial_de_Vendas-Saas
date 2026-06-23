from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from src.acoes import analisar_acoes_promocionais
from src.calculos import (
    calcular_indicadores,
    calcular_resumo_operacional,
    gerar_resultado_cliente,
    gerar_resultado_consultor,
)
from src.tratamento import preparar_acoes, preparar_base_vendas, preparar_painel_equipe, preparar_produtos_mix


def test_calcular_indicadores(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    indicadores = calcular_indicadores(vendas, clientes)

    assert indicadores["ol_sem_combate"] == 50
    assert indicadores["ol_prioritarios"] == 20
    assert indicadores["percentual_prioritarios"] == 0.4
    assert indicadores["ol_lancamentos"] == 30
    assert indicadores["percentual_lancamentos"] == 0.6
    assert indicadores["quantidade_pedidos"] == 3
    assert math.isclose(indicadores["ticket_medio"], 50 / 3)
    assert indicadores["clientes_positivados"] == 1
    assert indicadores["clientes_sem_compra"] == 1
    assert indicadores["clientes_ativos"] == 2
    assert indicadores["positivacao_percentual"] == 0.5


def test_calcular_resumo_operacional(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    resumo = calcular_resumo_operacional(vendas, clientes)

    assert resumo == {
        "valor_combate": 50.0,
        "faturado_periodo": 100.0,
        "clientes_ativos": 2,
        "clientes_com_venda": 1,
        "clientes_sem_venda": 1,
        "pedidos_faturados": 3,
        "valor_pedidos_faturados": 100.0,
        "pedidos_sem_nota": 2,
        "valor_sem_nota": 67.0,
        "pedidos_cancelados": 1,
        "valor_cancelado": 100.0,
    }


def test_gerar_resultado_cliente(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    resultado = gerar_resultado_cliente(vendas, clientes)
    alfa = resultado.loc[resultado["cnpj_limpo"].eq("12345678000190")].iloc[0]
    beta = resultado.loc[resultado["cnpj_limpo"].eq("98765432000110")].iloc[0]

    assert alfa["ol_sem_combate"] == 50
    assert alfa["ol_prioritarios"] == 20
    assert alfa["ol_lancamentos"] == 30
    assert alfa["status_comercial"] == "Comprou bem"
    assert beta["ol_sem_combate"] == 0
    assert beta["status_comercial"] == "Sem compra no per\u00edodo"


def test_gerar_resultado_consultor(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    resultado = gerar_resultado_consultor(vendas, clientes).set_index("consultor")

    assert resultado.loc["Ana", "clientes_na_base"] == 1
    assert resultado.loc["Ana", "clientes_com_compra"] == 1
    assert resultado.loc["Ana", "ol_sem_combate"] == 50
    assert resultado.loc["Bruno", "clientes_na_base"] == 1
    assert resultado.loc["Bruno", "clientes_com_compra"] == 0
    assert resultado.loc["Bruno", "clientes_sem_compra"] == 1


def test_analisar_acoes_promocionais(vendas: pd.DataFrame) -> None:
    acoes = preparar_acoes(
        pd.DataFrame(
            [
                {
                    "campanha": "Campanha Maio",
                    "produto": "Produto Prioritario",
                    "ean": "789123",
                    "tipo_mix": "PRIORITARIO",
                    "distribuidora": "CD Norte",
                    "desconto": "10",
                    "data_inicio": "01/05/2026",
                    "data_fim": "03/05/2026",
                    "consultor": "Ana",
                    "observacao": "",
                    "status": "ATIVA",
                }
            ]
        )
    )

    analise = analisar_acoes_promocionais(acoes, vendas)
    assert len(analise) == 1
    assert analise.iloc[0]["ol_durante_acao"] == 20
    assert analise.iloc[0]["quantidade_vendida"] == 2
    assert analise.iloc[0]["clientes_compradores"] == 1


def test_baseline_real_data_when_available(real_data_paths: dict[str, Path]) -> None:
    missing = [path for path in real_data_paths.values() if not path.exists()]
    if missing:
        pytest.skip("Bases reais locais nao disponiveis; fixture anonimizada continua cobrindo as regras.")

    raw_bussola = pd.read_excel(real_data_paths["bussola"], sheet_name="Pedidos", dtype=str, engine="openpyxl")
    raw_painel = pd.read_excel(real_data_paths["painel"], sheet_name="Planilha1", dtype=str, engine="openpyxl")
    raw_produtos = pd.read_excel(real_data_paths["produtos_mix"], dtype=str, engine="openpyxl")
    raw_acoes = pd.read_excel(real_data_paths["acoes"], dtype=str, engine="openpyxl")

    clientes = preparar_painel_equipe(raw_painel)
    produtos_mix = preparar_produtos_mix(raw_produtos)
    acoes = preparar_acoes(raw_acoes)
    vendas = preparar_base_vendas(raw_bussola, clientes, produtos_mix)

    assert raw_bussola.shape == (11952, 29)
    assert raw_painel.shape == (543, 47)
    assert raw_produtos.shape == (0, 3)
    assert raw_acoes.shape == (3, 11)
    assert vendas.shape == (11952, 54)
    assert clientes.shape == (543, 55)
    assert produtos_mix.shape == (0, 4)
    assert acoes.shape == (3, 12)
    assert str(vendas["data_base"].min().date()) == "2026-02-05"
    assert str(vendas["data_base"].max().date()) == "2026-05-05"

    indicadores = calcular_indicadores(vendas, clientes)
    assert indicadores["ol_sem_combate"] == pytest.approx(511082.95)
    assert indicadores["ol_prioritarios"] == 0.0
    assert indicadores["percentual_prioritarios"] == 0.0
    assert indicadores["ol_lancamentos"] == 0.0
    assert indicadores["percentual_lancamentos"] == 0.0
    assert indicadores["quantidade_pedidos"] == 1094
    assert indicadores["ticket_medio"] == pytest.approx(467.17, abs=0.01)
    assert indicadores["clientes_positivados"] == 62
    assert indicadores["clientes_sem_compra"] == 481
    assert indicadores["clientes_ativos"] == 543
    assert indicadores["positivacao_percentual"] == pytest.approx(0.114, abs=0.001)

    resumo = calcular_resumo_operacional(vendas, clientes)
    assert resumo["valor_combate"] == 0.0
    assert resumo["faturado_periodo"] == pytest.approx(511082.95)
    assert resumo["clientes_ativos"] == 543
    assert resumo["clientes_com_venda"] == 62
    assert resumo["clientes_sem_venda"] == 481
    assert resumo["pedidos_faturados"] == 1094
    assert resumo["valor_pedidos_faturados"] == pytest.approx(511082.95)
    assert resumo["pedidos_sem_nota"] == 26
    assert resumo["valor_sem_nota"] == pytest.approx(11394.19)
    assert resumo["pedidos_cancelados"] == 135
    assert resumo["valor_cancelado"] == 0.0
