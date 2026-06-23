from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd

from backend.core.tratamento import converter_numero, formatar_moeda, normalizar_cnpj, normalizar_ean, padronizar_colunas


COLUNAS_MERCADO = [
    "consultor",
    "uf",
    "cnpj_referencia",
    "ean",
    "produto",
    "distribuidora",
    "estoque",
    "desconto",
    "pf_dist",
    "pf_fabrica",
    "preco_com_imposto",
    "preco_sem_imposto",
    "data_atualizacao",
    "status",
    "erro",
]

VALID_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


def _texto(valor: object) -> str:
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def preparar_mercado_farma(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_MERCADO)
    base = df.copy()
    if all(str(col).startswith("Unnamed") for col in base.columns) and len(base) > 0:
        base.columns = base.iloc[0].tolist()
        base = base.iloc[1:].copy()
    base = padronizar_colunas(base)
    aliases = {
        "cnpj": "cnpj_referencia",
        "cnpj_ref": "cnpj_referencia",
        "cnpj_referencia": "cnpj_referencia",
        "ean": "ean",
        "nome_do_produto": "produto",
        "produto": "produto",
        "principio_ativo": "produto",
        "distribuidora": "distribuidora",
        "estoque": "estoque",
        "desconto": "desconto",
        "desconto_percent": "desconto",
        "desconto_percentual": "desconto",
        "pf_dist_r": "pf_dist",
        "pf_dist": "pf_dist",
        "pf_fabrica_r": "pf_fabrica",
        "pf_fabrica": "pf_fabrica",
        "preco_final_r": "preco_com_imposto",
        "preco_final": "preco_com_imposto",
        "preco_com_imposto": "preco_com_imposto",
        "sem_imposto_r": "preco_sem_imposto",
        "sem_imposto": "preco_sem_imposto",
        "preco_sem_imposto": "preco_sem_imposto",
        "data": "data_atualizacao",
        "data_atualizacao": "data_atualizacao",
        "status": "status",
        "erro": "erro",
        "uf": "uf",
        "consultor": "consultor",
        "consultor_usado": "consultor",
    }
    for origem, destino in aliases.items():
        if origem in base.columns and destino not in base.columns:
            base = base.rename(columns={origem: destino})
    for coluna in COLUNAS_MERCADO:
        if coluna not in base.columns:
            base[coluna] = 0 if coluna in {"estoque", "desconto", "pf_dist", "pf_fabrica", "preco_com_imposto", "preco_sem_imposto"} else ""

    base["cnpj_referencia"] = base["cnpj_referencia"].apply(normalizar_cnpj)
    base["ean"] = base["ean"].apply(normalizar_ean)
    for coluna in ["produto", "distribuidora", "consultor", "uf", "status", "erro"]:
        base[coluna] = base[coluna].apply(_texto)
    base["uf"] = base["uf"].str.upper()
    for coluna in ["estoque", "desconto", "pf_dist", "pf_fabrica", "preco_com_imposto", "preco_sem_imposto"]:
        base[coluna] = base[coluna].apply(converter_numero)
    base["desconto"] = base["desconto"].where(base["desconto"] <= 1, base["desconto"] / 100)
    base["data_atualizacao"] = pd.to_datetime(base["data_atualizacao"], errors="coerce", dayfirst=True)
    return base[COLUNAS_MERCADO].reset_index(drop=True)


def aplicar_descontos_adicionais(df: pd.DataFrame, configuracao: dict | None = None) -> pd.DataFrame:
    base = preparar_mercado_farma(df)
    if base.empty:
        return base
    dados = configuracao if isinstance(configuracao, dict) else {"distribuidoras": {}}
    regras = dados.get("distribuidoras", {}) if isinstance(dados, dict) else {}
    if not isinstance(regras, dict):
        return base
    for distribuidora, regra in regras.items():
        if not isinstance(regra, dict):
            continue
        percentual = converter_numero(regra.get("percentual", 0))
        if percentual > 1:
            percentual = percentual / 100
        percentual = max(min(percentual, 1), 0)
        if percentual <= 0:
            continue
        sem_desconto = {normalizar_ean(ean) for ean in regra.get("eans_sem_desconto", []) if normalizar_ean(ean)}
        mask = base["distribuidora"].astype(str).eq(str(distribuidora))
        if sem_desconto:
            mask = mask & ~base["ean"].astype(str).isin(sem_desconto)
        fator = 1 - percentual
        base.loc[mask, "preco_sem_imposto"] = base.loc[mask, "preco_sem_imposto"] * fator
        base.loc[mask, "preco_com_imposto"] = base.loc[mask, "preco_com_imposto"] * fator
        base.loc[mask, "desconto"] = (base.loc[mask, "desconto"] + percentual).clip(upper=1)
    return base


def ufs_validas_clientes(clientes: pd.DataFrame) -> list[str]:
    if clientes is None or clientes.empty or "uf" not in clientes.columns:
        return []
    base = clientes.copy()
    if "cliente_ativo" in base.columns:
        base = base[base["cliente_ativo"].fillna(True)].copy()
    ufs = base["uf"].dropna().astype(str).str.strip().str.upper()
    return sorted(uf for uf in ufs.unique().tolist() if uf in VALID_UFS)


def obter_eans_para_consulta(produtos_mercado_farma: pd.DataFrame) -> list[str]:
    if produtos_mercado_farma is None or produtos_mercado_farma.empty:
        return []
    base = padronizar_colunas(produtos_mercado_farma)
    coluna = "ean" if "ean" in base.columns else base.columns[0] if len(base.columns) else ""
    if not coluna:
        return []
    eans = base[coluna].dropna().astype(str).map(normalizar_ean)
    return sorted(ean for ean in eans.unique().tolist() if ean)


def melhor_preco_por_ean(df: pd.DataFrame) -> pd.DataFrame:
    base = preparar_mercado_farma(df)
    if base.empty:
        return base
    validos = base[(base["estoque"] > 0) & (base["preco_sem_imposto"] > 0)].copy()
    if validos.empty:
        return pd.DataFrame(columns=COLUNAS_MERCADO)
    return validos.sort_values(["uf", "ean", "preco_sem_imposto", "estoque"], ascending=[True, True, True, False]).drop_duplicates(["uf", "ean"])


def formatar_tabela_mercado(df: pd.DataFrame) -> pd.DataFrame:
    base = preparar_mercado_farma(df)
    colunas = {
        "consultor": "Consultor",
        "uf": "UF",
        "cnpj_referencia": "CNPJ referencia",
        "ean": "EAN",
        "produto": "Produto",
        "distribuidora": "Distribuidora",
        "estoque": "Estoque",
        "desconto": "Desconto",
        "pf_dist": "PF Dist.",
        "pf_fabrica": "PF Fabrica",
        "preco_com_imposto": "Preco com imposto",
        "preco_sem_imposto": "Preco sem imposto",
        "data_atualizacao": "Atualizado em",
        "status": "Status",
        "erro": "Erro",
    }
    base = base.rename(columns=colunas)
    for coluna in ["PF Dist.", "PF Fabrica", "Preco com imposto", "Preco sem imposto"]:
        if coluna in base.columns:
            base[coluna] = base[coluna].apply(formatar_moeda)
    if "Desconto" in base.columns:
        base["Desconto"] = base["Desconto"].apply(lambda valor: f"{float(valor or 0) * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
    if "Atualizado em" in base.columns:
        base["Atualizado em"] = pd.to_datetime(base["Atualizado em"], errors="coerce", dayfirst=True).dt.strftime("%d/%m/%Y %H:%M")
        base["Atualizado em"] = base["Atualizado em"].fillna("-")
    return base


def _ordenar_tabela_excel_mercado(base: pd.DataFrame) -> pd.DataFrame:
    if base.empty:
        return base
    ordenada = base.copy()
    if "Status" in ordenada.columns:
        status = ordenada["Status"].fillna("").astype(str).str.strip().str.upper()
        ordenada["_ordem_status"] = np.select([status.eq("OK"), status.eq("NAO ENCONTRADO")], [0, 1], default=2)
    else:
        ordenada["_ordem_status"] = 0
    ordenacao = [col for col in ["UF", "_ordem_status", "Produto", "EAN", "Distribuidora"] if col in ordenada.columns]
    ordenada = ordenada.sort_values(ordenacao, kind="stable").drop(columns=["_ordem_status"], errors="ignore")
    return ordenada.reset_index(drop=True)


def excel_mercado_farma_por_uf(df: pd.DataFrame) -> bytes:
    base = formatar_tabela_mercado(df).drop(columns=["Consultor"], errors="ignore")
    base = _ordenar_tabela_excel_mercado(base)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        if base.empty or "UF" not in base.columns:
            base.to_excel(writer, sheet_name="Mercado Farma", index=False)
        else:
            ufs = sorted(uf for uf in base["UF"].dropna().astype(str).str.strip().str.upper().unique().tolist() if uf)
            if not ufs:
                base.to_excel(writer, sheet_name="SEM_UF", index=False)
            for uf in ufs:
                df_uf = base[base["UF"].astype(str).str.upper().eq(uf)].copy()
                df_uf.to_excel(writer, sheet_name=uf[:31], index=False)
    return buffer.getvalue()

