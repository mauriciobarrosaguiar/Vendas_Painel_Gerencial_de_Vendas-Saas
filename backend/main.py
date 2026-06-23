from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.calculos import (  # noqa: E402
    calcular_indicadores,
    calcular_resumo_operacional,
    gerar_resultado_cliente,
    gerar_resultado_consultor,
)
from backend.core.loader_core import carregar_dados_tratados_de_arquivos  # noqa: E402
from backend.core.mercado_farma import melhor_preco_por_ean, preparar_mercado_farma  # noqa: E402
from backend.core.tratamento import (  # noqa: E402
    COLUNAS_ACOES,
    COLUNAS_BUSSOLA,
    COLUNAS_PAINEL,
    COLUNAS_PRODUTOS_MIX,
)

app = FastAPI(title="Painel Gerencial Norte API", version="0.1.0")


def _records(df: pd.DataFrame | None, limit: int = 200) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.head(limit).where(pd.notna(df), None).to_dict("records")


def _load_local_data() -> dict[str, Any]:
    dados = carregar_dados_tratados_de_arquivos(ROOT)
    vendas = dados.get("vendas")
    clientes = dados.get("clientes")
    if not isinstance(vendas, pd.DataFrame) or not isinstance(clientes, pd.DataFrame):
        raise RuntimeError("Bases tratadas nao foram carregadas.")
    return dados


def _unavailable(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "available": False,
            "message": "Nao foi possivel carregar as bases locais. Em producao, esta API deve ler Supabase Storage.",
            "error": str(exc),
        },
    )


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/dashboard")
def dashboard() -> Any:
    try:
        dados = _load_local_data()
        vendas = dados["vendas"]
        clientes = dados["clientes"]
        return {
            "available": True,
            "indicadores": calcular_indicadores(vendas, clientes),
            "resumo_operacional": calcular_resumo_operacional(vendas, clientes),
            "avisos": dados.get("avisos", []),
        }
    except Exception as exc:
        return _unavailable(exc)


@app.get("/consultores")
def consultores() -> Any:
    try:
        dados = _load_local_data()
        resultado = gerar_resultado_consultor(dados["vendas"], dados["clientes"])
        return {"available": True, "consultores": _records(resultado)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/clientes")
def clientes() -> Any:
    try:
        dados = _load_local_data()
        resultado = gerar_resultado_cliente(dados["vendas"], dados["clientes"])
        return {"available": True, "clientes": _records(resultado)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/mercado-farma")
def mercado_farma() -> Any:
    try:
        dados = _load_local_data()
        mercado = preparar_mercado_farma(dados["mercado_farma"])
        melhores = melhor_preco_por_ean(mercado)
        return {"available": True, "melhores_precos": _records(melhores)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/templates")
def templates() -> dict[str, Any]:
    return {
        "templates": {
            "bussola": COLUNAS_BUSSOLA,
            "painel": COLUNAS_PAINEL,
            "acoes": COLUNAS_ACOES,
            "produtos_mix": COLUNAS_PRODUTOS_MIX,
        }
    }


@app.get("/sip")
def sip_status() -> dict[str, Any]:
    return {
        "available": False,
        "message": "Endpoint preparado. Proxima etapa: carregar painel_sips do Supabase e aplicar backend.core.sip_calculos.",
    }


@app.post("/sip")
def sip_create() -> None:
    raise HTTPException(status_code=501, detail="Cadastro de SIP sera persistido em painel_sips.")


@app.get("/foco-semanal")
def foco_semanal_status() -> dict[str, Any]:
    return {"available": False, "message": "Usara backend.core.foco_semanal e painel_foco_semanal."}


@app.post("/foco-semanal")
def foco_semanal_create() -> None:
    raise HTTPException(status_code=501, detail="Persistencia via painel_foco_semanal.")


@app.post("/importacao")
def importacao() -> None:
    raise HTTPException(
        status_code=501,
        detail="Upload sera implementado com Supabase Storage, painel_bases, validacao e backup atomico.",
    )


@app.get("/exportar")
def exportar() -> None:
    raise HTTPException(status_code=501, detail="Exportacao Excel sera gerada a partir das tabelas da API.")
