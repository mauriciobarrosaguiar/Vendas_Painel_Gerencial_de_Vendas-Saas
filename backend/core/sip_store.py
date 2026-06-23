from __future__ import annotations

import pandas as pd

from .tratamento import normalizar_cnpj, slug_coluna


STATUS_RECADOS_VALIDOS = {"Pendente", "Em andamento", "Concluido", "Conclu\u00eddo"}


def normalizar_chave_sip(texto: object) -> str:
    return slug_coluna(texto)


def normalizar_grupo_sip(grupo: dict) -> dict:
    nome = str(grupo.get("nome", "")).strip()
    gid = normalizar_chave_sip(grupo.get("id") or nome)
    cnpjs = [normalizar_cnpj(cnpj) for cnpj in grupo.get("cnpjs", [])]
    cnpjs = sorted({cnpj for cnpj in cnpjs if cnpj})
    redes = sorted({str(rede).strip() for rede in grupo.get("redes", []) if str(rede).strip()})
    recados = grupo.get("recados", [])
    if not isinstance(recados, list):
        recados = []
    return {
        "id": gid,
        "nome": nome,
        "redes": redes,
        "cnpjs": cnpjs,
        "meta_mes": float(grupo.get("meta_mes", 0) or 0),
        "pagamento_percentual": float(grupo.get("pagamento_percentual", 80) or 80),
        "recados": [recado for recado in recados if isinstance(recado, dict)],
    }


def opcoes_clientes_para_sip(clientes_resultado: pd.DataFrame) -> pd.DataFrame:
    if clientes_resultado.empty:
        return pd.DataFrame(columns=["label", "cnpj_limpo", "rede"])
    base = clientes_resultado[["cnpj_limpo", "nome_pdv", "cidade", "uf", "consultor", "grupo_sip"]].copy()
    base["rede"] = base["grupo_sip"].fillna("").astype(str)
    base["label"] = (
        base["nome_pdv"].fillna("").astype(str)
        + " - "
        + base["cnpj_limpo"].fillna("").astype(str)
        + " - "
        + base["rede"].fillna("").astype(str)
    )
    return base.sort_values(["rede", "nome_pdv", "cnpj_limpo"]).reset_index(drop=True)


def gerar_resumo_sips_manuais(clientes_resultado: pd.DataFrame, grupos: list[dict]) -> pd.DataFrame:
    grupos_norm = [normalizar_grupo_sip(grupo) for grupo in grupos]
    if not grupos_norm:
        return pd.DataFrame(
            columns=[
                "sip",
                "redes",
                "cnpjs",
                "consultores",
                "ol_sem_combate",
                "ol_prioritarios",
                "percentual_prioritarios",
                "ol_lancamentos",
                "percentual_lancamentos",
                "cnpjs_com_compra",
                "cnpjs_sem_compra",
                "meta_mes",
                "atingimento_meta",
            ]
        )

    clientes = clientes_resultado.copy()
    linhas: list[dict[str, object]] = []
    for grupo in grupos_norm:
        membros = clientes[clientes["cnpj_limpo"].astype(str).isin(grupo["cnpjs"])].copy()
        ol_sem = float(membros["ol_sem_combate"].sum()) if not membros.empty else 0.0
        ol_pri = float(membros["ol_prioritarios"].sum()) if not membros.empty else 0.0
        ol_lan = float(membros["ol_lancamentos"].sum()) if not membros.empty else 0.0
        linhas.append(
            {
                "sip": grupo["nome"],
                "id": grupo["id"],
                "redes": ", ".join(grupo["redes"]),
                "cnpjs": len(grupo["cnpjs"]),
                "consultores": ", ".join(sorted({str(x) for x in membros.get("consultor", pd.Series(dtype=str)) if str(x).strip()})),
                "ol_sem_combate": ol_sem,
                "ol_prioritarios": ol_pri,
                "percentual_prioritarios": (ol_pri / ol_sem) if ol_sem else 0.0,
                "ol_lancamentos": ol_lan,
                "percentual_lancamentos": (ol_lan / ol_sem) if ol_sem else 0.0,
                "cnpjs_com_compra": int((membros["ol_sem_combate"] > 0).sum()) if not membros.empty else 0,
                "cnpjs_sem_compra": int((membros["ol_sem_combate"] <= 0).sum()) if not membros.empty else len(grupo["cnpjs"]),
                "meta_mes": grupo["meta_mes"],
                "atingimento_meta": (ol_sem / grupo["meta_mes"]) if grupo["meta_mes"] else 0.0,
            }
        )
    return pd.DataFrame(linhas).sort_values(["ol_sem_combate", "sip"], ascending=[False, True]).reset_index(drop=True)

