from __future__ import annotations

import pandas as pd

from .tratamento import STATUS_CANCELADO, STATUS_FATURADOS


def _opcoes(series: pd.Series) -> list[str]:
    if series is None or series.empty:
        return []
    valores = series.dropna().astype(str).str.strip()
    valores = valores[valores.ne("")]
    return sorted(valores.unique().tolist())


def _datas_faturamento(vendas: pd.DataFrame) -> pd.Series:
    if vendas is None or vendas.empty or "data_de_faturamento" not in vendas.columns:
        indice = vendas.index if isinstance(vendas, pd.DataFrame) else None
        return pd.Series(pd.NaT, index=indice, dtype="datetime64[ns]")
    return pd.to_datetime(vendas["data_de_faturamento"], errors="coerce")


def calcular_opcoes_filtros(vendas: pd.DataFrame, clientes: pd.DataFrame) -> dict[str, list[str]]:
    vendas = vendas.copy() if vendas is not None else pd.DataFrame()
    clientes = clientes.copy() if clientes is not None else pd.DataFrame()
    consultores_fontes: list[pd.Series] = []
    if "nome_rep" in clientes.columns:
        consultores_fontes.append(clientes["nome_rep"])
    if "consultor" in vendas.columns:
        consultores_fontes.append(vendas["consultor"])
    consultores = pd.concat(consultores_fontes, ignore_index=True) if consultores_fontes else pd.Series(dtype=str)
    consultores = consultores.dropna().astype(str).str.strip()
    consultores = consultores[consultores.ne("")]
    consultores = consultores[~consultores.str.contains(r"\s*/\s*", regex=True, na=False)]
    consultores_map: dict[str, str] = {}
    for valor in consultores:
        consultores_map.setdefault(" ".join(valor.upper().split()), valor)

    datas = _datas_faturamento(vendas).dropna()
    meses = sorted(datas.dt.to_period("M").astype(str).unique().tolist()) if not datas.empty else []
    ufs = pd.concat(
        [clientes.get("uf", pd.Series(dtype=str)), vendas.get("uf", pd.Series(dtype=str))],
        ignore_index=True,
    )
    return {
        "meses": meses,
        "consultores": [consultores_map[chave] for chave in sorted(consultores_map)],
        "distribuidoras": _opcoes(vendas.get("distribuidora", pd.Series(dtype=str))),
        "ufs": _opcoes(ufs),
        "cidades": _opcoes(clientes.get("cidade", pd.Series(dtype=str))),
        "grupos_sip": _opcoes(clientes.get("grupo_sip", pd.Series(dtype=str))),
        "status": _opcoes(vendas.get("status_normalizado", pd.Series(dtype=str))),
        "tipos_mix": _opcoes(vendas.get("tipo_mix", pd.Series(dtype=str))),
    }


def filtrar_periodo_faturamento(
    vendas: pd.DataFrame,
    inicio: object,
    fim: object,
    apenas_faturados: bool = True,
) -> pd.DataFrame:
    if vendas is None or vendas.empty:
        return vendas.copy() if vendas is not None else pd.DataFrame()

    base = vendas.copy()
    inicio_ts = pd.Timestamp(inicio).normalize()
    fim_ts = pd.Timestamp(fim).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    datas = _datas_faturamento(base)
    filtrada = base[(datas >= inicio_ts) & (datas <= fim_ts)].copy()

    if apenas_faturados and "status_normalizado" in filtrada.columns:
        filtrada = filtrada[filtrada["status_normalizado"].isin(STATUS_FATURADOS)].copy()
    return filtrada


def _aplicar_filtro_status(vendas: pd.DataFrame, modo: str, status_sel: list[str] | None = None) -> pd.DataFrame:
    if vendas.empty or "status_normalizado" not in vendas.columns:
        return vendas.copy()
    status_sel = status_sel or []
    if modo == "Apenas faturados":
        return vendas[vendas["status_normalizado"].isin(STATUS_FATURADOS)].copy()
    if modo == "Todos exceto cancelados":
        return vendas[vendas["status_normalizado"].ne(STATUS_CANCELADO)].copy()
    if status_sel:
        return vendas[vendas["status_normalizado"].isin(status_sel)].copy()
    return vendas.copy()


def filtrar_busca(df: pd.DataFrame, termo: str, colunas: list[str] | None = None) -> pd.DataFrame:
    if df.empty or not termo:
        return df
    termo_norm = termo.strip().lower()
    colunas_busca = colunas or df.select_dtypes(include="object").columns.tolist()
    mascara = pd.Series(False, index=df.index)
    for coluna in colunas_busca:
        if coluna in df.columns:
            mascara = mascara | df[coluna].astype(str).str.lower().str.contains(termo_norm, na=False, regex=False)
    return df[mascara].copy()


def aplicar_filtros_clientes(clientes: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    base = clientes.copy() if clientes is not None else pd.DataFrame()
    if base.empty:
        return base
    for chave, coluna in [("consultor", "nome_rep"), ("uf", "uf"), ("cidade", "cidade"), ("grupo_sip", "grupo_sip")]:
        valores = filtros.get(chave) or []
        if valores and coluna in base.columns:
            base = base[base[coluna].isin(valores)].copy()
    return base


def aplicar_filtros_vendas(vendas: pd.DataFrame, clientes_filtrados: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    base = filtrar_periodo_faturamento(vendas, filtros.get("inicio"), filtros.get("fim"), apenas_faturados=False)
    base = _aplicar_filtro_status(base, str(filtros.get("status_modo") or "Apenas faturados"), filtros.get("status") or [])
    for chave, coluna in [
        ("consultor", "consultor"),
        ("distribuidora", "distribuidora"),
        ("uf", "uf"),
        ("cidade", "cidade"),
        ("grupo_sip", "grupo_sip"),
        ("tipo_mix", "tipo_mix"),
    ]:
        valores = filtros.get(chave) or []
        if valores and coluna in base.columns:
            base = base[base[coluna].isin(valores)].copy()

    if filtros.get("restringir_por_clientes") and clientes_filtrados is not None and not clientes_filtrados.empty:
        cnpjs = set(clientes_filtrados["cnpj_limpo"].dropna().astype(str))
        base = base[base["cnpj_limpo"].astype(str).isin(cnpjs)].copy()
    return base


def aplicar_filtros_globais_core(
    vendas: pd.DataFrame,
    clientes: pd.DataFrame,
    filtros: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    filtros_norm = {
        "inicio": filtros.get("inicio"),
        "fim": filtros.get("fim"),
        "consultor": filtros.get("consultor") or [],
        "distribuidora": filtros.get("distribuidora") or [],
        "uf": filtros.get("uf") or [],
        "cidade": filtros.get("cidade") or [],
        "grupo_sip": filtros.get("grupo_sip") or [],
        "status_modo": filtros.get("status_modo") or "Apenas faturados",
        "status": filtros.get("status") or [],
        "tipo_mix": filtros.get("tipo_mix") or [],
    }
    filtros_norm["restringir_por_clientes"] = bool(
        filtros_norm["consultor"] or filtros_norm["uf"] or filtros_norm["cidade"] or filtros_norm["grupo_sip"]
    )
    clientes_filtrados = aplicar_filtros_clientes(clientes, filtros_norm)
    vendas_filtradas = aplicar_filtros_vendas(vendas, clientes_filtrados, filtros_norm)
    return vendas_filtradas, clientes_filtrados, filtros_norm


def filtrar_vendas_operacionais(
    vendas: pd.DataFrame,
    clientes_filtrados: pd.DataFrame,
    filtros: dict[str, object],
    aplicar_status: bool = False,
) -> pd.DataFrame:
    if vendas.empty:
        return vendas.copy()
    inicio = pd.Timestamp(filtros.get("inicio")).normalize()
    fim = pd.Timestamp(filtros.get("fim")).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    base = vendas.copy()

    data_faturamento = _datas_faturamento(base)
    fallback_data_pedido = pd.Series(pd.NaT, index=base.index)
    data_pedido = pd.to_datetime(
        base["data_base"] if "data_base" in base.columns else base.get("data_do_pedido", fallback_data_pedido),
        errors="coerce",
    )
    status = (
        base["status_normalizado"].fillna("").astype(str)
        if "status_normalizado" in base.columns
        else pd.Series("", index=base.index)
    )
    if "pedido_sem_nota" in base.columns:
        pedido_sem_nota = base["pedido_sem_nota"].fillna(False).astype(bool)
    else:
        nota_vazia = (
            base["nota_fiscal"].fillna("").astype(str).str.strip().eq("")
            if "nota_fiscal" in base.columns
            else pd.Series(False, index=base.index)
        )
        pedido_sem_nota = nota_vazia & status.ne(STATUS_CANCELADO)
    usar_data_pedido = pedido_sem_nota | status.eq(STATUS_CANCELADO) | data_faturamento.isna()
    datas_operacionais = data_faturamento.where(~usar_data_pedido, data_pedido)
    base = base[(datas_operacionais >= inicio) & (datas_operacionais <= fim)].copy()

    if aplicar_status:
        base = _aplicar_filtro_status(base, str(filtros.get("status_modo") or ""), filtros.get("status") or [])

    for coluna_filtro, coluna_base in [
        ("distribuidora", "distribuidora"),
        ("uf", "uf"),
        ("cidade", "cidade"),
        ("grupo_sip", "grupo_sip"),
        ("tipo_mix", "tipo_mix"),
        ("consultor", "consultor"),
    ]:
        valores = filtros.get(coluna_filtro) or []
        if valores:
            base = base[base[coluna_base].isin(valores)].copy()

    if filtros.get("restringir_por_clientes") and clientes_filtrados is not None:
        cnpjs = set(clientes_filtrados["cnpj_limpo"].dropna().astype(str))
        base = base[base["cnpj_limpo"].astype(str).isin(cnpjs)].copy()

    return base

