from __future__ import annotations

import math

import pandas as pd

from src.projecao import calcular_projecao, classe_projecao, dias_uteis
from src.sip_calculos import calcular_indicadores_sip


def test_sip_calculos(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    grupo = {
        "id": "rede-teste",
        "nome": "Rede Teste",
        "cnpjs": ["12345678000190", "98765432000110"],
        "redes": ["Rede Boa"],
        "meta_mes": 100,
        "pagamento_percentual": 80,
    }

    resultado = calcular_indicadores_sip(vendas, clientes, grupo, "2026-05-01", "2026-05-31", "Todos")

    assert resultado["cnpjs"] == 2
    assert resultado["faturado"] == 50
    assert resultado["ol_prioritarios"] == 20
    assert resultado["ol_lancamentos"] == 30
    assert resultado["falta_regra"] == 30
    assert resultado["atingimento"] == 0.5
    assert resultado["pedidos_faturados"] == 2
    assert resultado["pedidos_sem_nota"] == 2
    assert resultado["pedidos_cancelados"] == 1
    assert resultado["valor_pedidos_faturados"] == 50
    assert resultado["valor_sem_nota"] == 67
    assert resultado["valor_cancelado"] == 100


def test_sip_filtro_status(vendas: pd.DataFrame, clientes: pd.DataFrame) -> None:
    grupo = {
        "id": "rede-teste",
        "nome": "Rede Teste",
        "cnpjs": ["12345678000190", "98765432000110"],
        "meta_mes": 100,
        "pagamento_percentual": 80,
    }

    resultado = calcular_indicadores_sip(vendas, clientes, grupo, "2026-05-01", "2026-05-31", "Sem nota")

    assert resultado["linhas_pedidos_usados"] == 2
    assert resultado["pedidos_sem_nota"] == 2
    assert resultado["faturado"] == 0


def test_projecao_dias_uteis_e_classes() -> None:
    uteis = dias_uteis("2026-05-01", "2026-05-31")
    assert uteis == 20

    projecao = calcular_projecao(100, 200, "2026-05-01", "2026-05-15")
    assert projecao["dias_uteis_periodo"] == 20
    assert projecao["dias_uteis_decorridos"] == 10
    assert projecao["projetado"] == 200
    assert math.isclose(projecao["percentual"], 1.0)

    assert classe_projecao(1.2) == ("projection-green", "\u2605")
    assert classe_projecao(1.0) == ("projection-blue", "")
    assert classe_projecao(0.9) == ("projection-orange", "")
    assert classe_projecao(0.8) == ("projection-dark-red", "")
    assert classe_projecao(0.79) == ("projection-red", "")
