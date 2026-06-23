from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from backend.core.tratamento import CHAVES_DEDUP_PEDIDOS, padronizar_colunas


CHAVES_META = ["ol_sem_combate", "ol_prioritarios", "ol_lancamentos", "clientes_positivados"]
CHAVES_META_OPCIONAIS = ["demanda_sem_combate"]


def meta_padrao_mes() -> dict[str, Any]:
    return {
        "gerente_territorial": {
            "ol_sem_combate": 0.0,
            "ol_prioritarios": 0.0,
            "ol_lancamentos": 0.0,
            "clientes_positivados": 0.0,
        },
        "consultores": {},
    }


def _numero(valor: object) -> float:
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return 0.0
    return numero if pd.notna(numero) else 0.0


def _normalizar_meta(meta: dict[str, object] | None) -> dict[str, float]:
    meta = meta or {}
    normalizada = {chave: _numero(meta.get(chave, 0)) for chave in CHAVES_META}
    for chave in CHAVES_META_OPCIONAIS:
        if chave in meta:
            normalizada[chave] = _numero(meta.get(chave, 0))
    return normalizada


def metas_para_periodo(metas_atuais: dict[str, Any], filtros: dict[str, object], metas_historico: dict[str, Any] | None = None) -> dict[str, Any]:
    if not filtros.get("usar_metas_historicas"):
        return metas_atuais
    ano_mes = str(filtros.get("mes_referencia") or "")
    if not ano_mes:
        return metas_atuais

    meta_mes = (metas_historico or {}).get("meses", {}).get(ano_mes, {})
    if not isinstance(meta_mes, dict):
        return metas_atuais

    metas = deepcopy(metas_atuais)
    if isinstance(meta_mes.get("gerente_territorial"), dict):
        metas["gerente_territorial"] = _normalizar_meta(meta_mes["gerente_territorial"])
    if isinstance(meta_mes.get("consultores"), dict):
        metas.setdefault("consultores", {})
        for consultor, meta in meta_mes["consultores"].items():
            if isinstance(meta, dict):
                metas["consultores"][str(consultor)] = _normalizar_meta(meta)
    return metas


def combinar_bases_bussola_historico(base_importacao: pd.DataFrame, base_historico: pd.DataFrame) -> pd.DataFrame:
    partes = [df for df in [base_historico, base_importacao] if df is not None and not df.empty]
    if not partes:
        return pd.DataFrame()

    combinado = pd.concat(partes, ignore_index=True)
    base = padronizar_colunas(combinado)
    chaves = [coluna for coluna in CHAVES_DEDUP_PEDIDOS if coluna in base.columns]
    if len(chaves) != len(CHAVES_DEDUP_PEDIDOS):
        return combinado

    chave_texto = base[chaves].astype("string").fillna("")
    mascara_chave_vazia = chave_texto.eq("").all(axis=1)
    deduplicado = base.loc[~mascara_chave_vazia].drop_duplicates(chaves, keep="last")
    sem_chave = base.loc[mascara_chave_vazia]
    return pd.concat([deduplicado, sem_chave], ignore_index=True)

