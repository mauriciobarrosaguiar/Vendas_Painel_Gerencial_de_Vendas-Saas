from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.tratamento import preparar_base_vendas, preparar_painel_equipe, preparar_produtos_mix


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw_clientes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "CNPJ": "12.345.678/0001-90",
                "NOME PDV": "Farmacia Alfa",
                "CIDADE": "Sao Luis",
                "UF": "MA",
                "SITUACAO": "ATIVO",
                "GRUPO ECONOMICO": "Rede Boa",
                "REDE ASSOCIACAO": "",
                "BANDEIRA": "",
                "NOME GD": "GD Norte",
                "NOME REP": "Ana",
                "SETOR REP": "101",
                "FOCO PEX": "SIM",
                "POSITIVACAO": "SIM",
            },
            {
                "CNPJ": "98.765.432/0001-10",
                "NOME PDV": "Loja Beta",
                "CIDADE": "Belem",
                "UF": "PA",
                "SITUACAO": "ATIVO",
                "GRUPO ECONOMICO": "",
                "REDE ASSOCIACAO": "",
                "BANDEIRA": "",
                "NOME GD": "GD Norte",
                "NOME REP": "Bruno",
                "SETOR REP": "102",
                "FOCO PEX": "",
                "POSITIVACAO": "",
            },
            {
                "CNPJ": "",
                "NOME PDV": "Cliente Invalido",
                "CIDADE": "Palmas",
                "UF": "TO",
                "SITUACAO": "INATIVO",
                "GRUPO ECONOMICO": "",
                "REDE ASSOCIACAO": "",
                "BANDEIRA": "",
                "NOME GD": "GD Norte",
                "NOME REP": "Carla",
                "SETOR REP": "103",
                "FOCO PEX": "",
                "POSITIVACAO": "",
            },
        ]
    )


@pytest.fixture
def raw_produtos_mix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"EAN": "789-123", "Produto": "Produto Prioritario", "Tipo Mix": "prioritarios"},
            {"EAN": "456", "Produto": "Produto Lancamento", "Tipo Mix": "lancamentos"},
            {"EAN": "999", "Produto": "Produto Combate", "Tipo Mix": "combate"},
        ]
    )


@pytest.fixture
def raw_vendas() -> pd.DataFrame:
    def row(
        pedido: str,
        status: str,
        nota: str,
        cnpj: str,
        ean: str,
        produto: str,
        quantidade_faturada: object,
        quantidade_atendida: object,
        preco: object,
        valor_faturado: object,
        valor_solicitado: object,
    ) -> dict[str, object]:
        return {
            "status_pedido": status,
            "nota_fiscal": nota,
            "pedido_id": pedido,
            "data_do_pedido": "01/05/2026",
            "data_de_faturamento": "02/05/2026",
            "canal_de_vendas": "Web",
            "cod_representante": "1",
            "representante": "Representante",
            "cnpj_pdv": cnpj,
            "centro_distribuicao": "CD Norte",
            "uf_centro_distribuicao": "MA",
            "ean": ean,
            "sku_produto": f"SKU-{ean}",
            "produto": produto,
            "quantidade_solicitada": quantidade_faturada,
            "quantidade_atendida": quantidade_atendida,
            "quantidade_faturada": quantidade_faturada,
            "quantidade_cancelada": "0",
            "preco_unitario_com_imposto": preco,
            "preco_unitario_sem_imposto": preco,
            "desconto_digitado": "0",
            "desconto_aplicado_em_nota": "0",
            "valor_total_solicitado_com_imposto": valor_solicitado,
            "valor_total_solicitado_sem_imposto": valor_solicitado,
            "total_atendido_sem_imposto": valor_faturado,
            "total_atendido_com_imposto": valor_faturado,
            "valor_faturado": valor_faturado,
        }

    return pd.DataFrame(
        [
            row("P1", "Faturado", "NF1", "12.345.678/0001-90", "789123", "Produto Prioritario", "2", "0", "10", "20", "20"),
            row("P2", "Faturado Parcial", "NF2", "12.345.678/0001-90", "456", "Produto Lancamento", "1", "0", "30", "30", "30"),
            row("P3", "Cancelado", "", "12.345.678/0001-90", "789123", "Produto Prioritario", "1", "0", "100", "100", "100"),
            row("P4", "Faturado Recuperado", "", "98.765.432/0001-10", "999", "Produto Combate", "5", "0", "10", "50", "55"),
            row("P5", "Em aberto", "", "98.765.432/0001-10", "456", "Produto Lancamento", "0", "0", "12", "0", "12"),
        ]
    )


@pytest.fixture
def clientes(raw_clientes: pd.DataFrame) -> pd.DataFrame:
    return preparar_painel_equipe(raw_clientes)


@pytest.fixture
def produtos_mix(raw_produtos_mix: pd.DataFrame) -> pd.DataFrame:
    return preparar_produtos_mix(raw_produtos_mix)


@pytest.fixture
def vendas(raw_vendas: pd.DataFrame, clientes: pd.DataFrame, produtos_mix: pd.DataFrame) -> pd.DataFrame:
    return preparar_base_vendas(raw_vendas, clientes, produtos_mix)


@pytest.fixture
def real_data_paths() -> dict[str, Path]:
    return {
        "bussola": ROOT / "data" / "bussola.xlsx",
        "painel": ROOT / "data" / "PAINEL EQUIPE NORTE.xlsx",
        "produtos_mix": ROOT / "data" / "template_produtos_mix.xlsx",
        "acoes": ROOT / "data" / "template_acoes_promocionais.xlsx",
    }

