from __future__ import annotations

import pandas as pd

from src.tratamento import (
    STATUS_CANCELADO,
    deduplicar_pedidos_bussola,
    normalizar_cnpj,
    normalizar_ean,
    normalizar_tipo_mix,
    preparar_base_vendas,
    preparar_painel_equipe,
    preparar_produtos_mix,
    status_pedido_normalizado,
)


def test_normalizar_cnpj() -> None:
    assert normalizar_cnpj("12.345.678/0001-90") == "12345678000190"
    assert normalizar_cnpj("123") == "00000000000123"
    assert normalizar_cnpj("") == ""


def test_normalizar_ean() -> None:
    assert normalizar_ean("789-123 abc") == "789123"
    assert normalizar_ean(None) == ""


def test_status_pedido_normalizado() -> None:
    assert status_pedido_normalizado("pedido cancelado") == STATUS_CANCELADO
    assert status_pedido_normalizado("Faturado recuperado") == "FATURADO RECUPERADO"
    assert status_pedido_normalizado("Faturado parcial") == "FATURADO PARCIAL"
    assert status_pedido_normalizado("Faturado") == "FATURADO"
    assert status_pedido_normalizado("") == "SEM STATUS"


def test_normalizar_tipo_mix() -> None:
    assert normalizar_tipo_mix("prioritarios") == "PRIORITARIO"
    assert normalizar_tipo_mix("prioritarias") == "PRIORITARIO"
    assert normalizar_tipo_mix("lancamentos") == "LANCAMENTO"
    assert normalizar_tipo_mix("linha") == "LINHA"
    assert normalizar_tipo_mix("combate") == "COMBATE"
    assert normalizar_tipo_mix("") == "SEM CLASSIFICACAO"


def test_preparar_painel_equipe(raw_clientes: pd.DataFrame) -> None:
    clientes = preparar_painel_equipe(raw_clientes)
    alfa = clientes.loc[clientes["nome_pdv"].eq("Farmacia Alfa")].iloc[0]
    beta = clientes.loc[clientes["nome_pdv"].eq("Loja Beta")].iloc[0]
    invalido = clientes.loc[clientes["nome_pdv"].eq("Cliente Invalido")].iloc[0]

    assert alfa["cnpj_limpo"] == "12345678000190"
    assert alfa["grupo_sip"] == "REDE BOA"
    assert beta["grupo_sip"] == "LOJA BETA"
    assert bool(alfa["cliente_ativo"]) is True
    assert bool(invalido["cliente_ativo"]) is False


def test_preparar_produtos_mix(raw_produtos_mix: pd.DataFrame) -> None:
    produtos = preparar_produtos_mix(raw_produtos_mix)
    assert produtos.shape == (3, 4)
    assert set(produtos["tipo_mix"]) == {"PRIORITARIO", "LANCAMENTO", "COMBATE"}
    assert "789123" in set(produtos["ean_limpo"])


def test_preparar_base_vendas(vendas: pd.DataFrame) -> None:
    assert vendas.shape[0] == 5
    p1 = vendas.loc[vendas["pedido_id"].eq("P1")].iloc[0]
    p4 = vendas.loc[vendas["pedido_id"].eq("P4")].iloc[0]
    p5 = vendas.loc[vendas["pedido_id"].eq("P5")].iloc[0]

    assert p1["cnpj_limpo"] == "12345678000190"
    assert p1["ean_limpo"] == "789123"
    assert p1["status_normalizado"] == "FATURADO"
    assert p1["tipo_mix"] == "PRIORITARIO"
    assert p1["quantidade_base"] == 2
    assert p1["valor_calculado_sem_imposto"] == 20
    assert p1["valor_vendido_sem_imposto"] == 20

    assert bool(p4["pedido_sem_nota"]) is True
    assert p4["valor_sem_nota_sem_imposto"] == 55
    assert p4["valor_pedido_sem_imposto"] == 55

    assert bool(p5["pedido_sem_nota"]) is True
    assert p5["valor_sem_nota_sem_imposto"] == 12
    assert p5["valor_pedido_sem_imposto"] == 12


def test_deduplicar_pedidos_bussola(raw_vendas: pd.DataFrame, clientes: pd.DataFrame, produtos_mix: pd.DataFrame) -> None:
    duplicada = raw_vendas.iloc[[0]].copy()
    duplicada.loc[duplicada.index[0], "produto"] = "Produto Prioritario Atualizado"
    base = pd.concat([raw_vendas.iloc[[0]], duplicada], ignore_index=True)
    vendas = preparar_base_vendas(base, clientes, produtos_mix)

    assert len(vendas) == 1
    assert vendas.iloc[0]["produto"] == "Produto Prioritario Atualizado"
    assert len(deduplicar_pedidos_bussola(vendas)) == 1

