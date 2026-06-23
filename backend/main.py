from __future__ import annotations

import hashlib
import mimetypes
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

CURRENT_DIR = Path(__file__).resolve().parent
ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "backend" else CURRENT_DIR
for path in (ROOT, CURRENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from backend.core.calculos import (
        calcular_indicadores,
        calcular_resumo_operacional,
        gerar_resultado_cliente,
        gerar_resultado_consultor,
    )
    from backend.core.loader_core import (
        BasesRaw,
        carregar_dados_tratados_de_arquivos,
        ler_base_bytes,
        tratar_bases,
        validar_upload_generico,
    )
    from backend.core.mercado_farma import melhor_preco_por_ean, preparar_mercado_farma
    from backend.core.tratamento import (
        COLUNAS_ACOES,
        COLUNAS_BUSSOLA,
        COLUNAS_PAINEL,
        COLUNAS_PRODUTOS_MIX,
    )
    from backend.services.supabase_client import (
        SupabaseConfigError,
        get_default_empresa_id,
        get_supabase_client,
        is_supabase_configured,
        resolve_user_context,
    )
except ModuleNotFoundError as exc:
    if exc.name not in {"backend", "backend.core", "backend.services"}:
        raise
    from core.calculos import (
        calcular_indicadores,
        calcular_resumo_operacional,
        gerar_resultado_cliente,
        gerar_resultado_consultor,
    )
    from core.loader_core import (
        BasesRaw,
        carregar_dados_tratados_de_arquivos,
        ler_base_bytes,
        tratar_bases,
        validar_upload_generico,
    )
    from core.mercado_farma import melhor_preco_por_ean, preparar_mercado_farma
    from core.tratamento import (
        COLUNAS_ACOES,
        COLUNAS_BUSSOLA,
        COLUNAS_PAINEL,
        COLUNAS_PRODUTOS_MIX,
    )
    from services.supabase_client import (
        SupabaseConfigError,
        get_default_empresa_id,
        get_supabase_client,
        is_supabase_configured,
        resolve_user_context,
    )


app = FastAPI(title="Painel Gerencial Norte API", version="0.2.0")

BUCKET_NAME = "painel-bases"
TIPOS_BASE: dict[str, str] = {
    "bussola": "Bussola",
    "painel": "Painel clientes",
    "produtos_mix": "Produtos / Mix",
    "acoes": "Acoes promocionais",
    "mercado_farma": "Mercado Farma",
    "produtos_mercado_farma": "Produtos Mercado Farma",
    "bussola_historico": "Historico Bussola",
}
EXTENSOES_VALIDAS = {".xlsx", ".xls", ".csv"}


def _records(df: pd.DataFrame | None, limit: int = 200) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    data = df.head(limit).where(pd.notna(df), None).to_dict("records")
    return jsonable_encoder(data)


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
            "ok": False,
            "available": False,
            "message": "Falha ao carregar dados. Verifique configuracao da API/Supabase.",
            "error": str(exc),
        },
    )


def _empty_dashboard(
    *,
    message: str = "Nenhuma base importada ainda",
    supabase_connected: bool = False,
    bases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "empty": True,
        "available": False,
        "api_connected": True,
        "supabase_connected": supabase_connected,
        "message": message,
        "indicadores": {},
        "resumo": {},
        "resumo_operacional": {},
        "dados": [],
        "bases": bases or [],
    }


def _base_statuses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    by_type = {str(row.get("tipo_base")): row for row in rows}
    for tipo, nome in TIPOS_BASE.items():
        row = by_type.get(tipo)
        statuses.append(
            {
                "name": nome,
                "type": tipo,
                "updatedAt": str(row.get("created_at") or "-") if row else "-",
                "source": "Supabase Storage",
                "status": "ok" if row else "missing",
            }
        )
    return statuses


def _safe_filename(filename: str) -> str:
    name = Path(filename or "base").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "base.xlsx"


def _content_type(filename: str, fallback: str | None) -> str:
    guessed = mimetypes.guess_type(filename)[0]
    return fallback or guessed or "application/octet-stream"


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _active_base_rows(client: Any, empresa_id: str | None) -> list[dict[str, Any]]:
    query = (
        client.table("painel_bases")
        .select("id,empresa_id,tipo_base,nome_arquivo,storage_path,linhas,colunas,hash_arquivo,ativo,created_at")
        .eq("ativo", True)
        .order("created_at", desc=True)
    )
    if empresa_id:
        query = query.eq("empresa_id", empresa_id)
    response = query.execute()
    rows = response.data if isinstance(response.data, list) else []
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        tipo = str(row.get("tipo_base") or "")
        if tipo in TIPOS_BASE and tipo not in latest:
            latest[tipo] = row
    return list(latest.values())


def _download_active_files(client: Any, rows: list[dict[str, Any]]) -> dict[str, tuple[bytes, str]]:
    bucket = client.storage.from_(BUCKET_NAME)
    files: dict[str, tuple[bytes, str]] = {}
    for row in rows:
        tipo = str(row.get("tipo_base") or "")
        path = str(row.get("storage_path") or "")
        if tipo not in TIPOS_BASE or not path:
            continue
        files[tipo] = (bucket.download(path), str(row.get("nome_arquivo") or path))
    return files


def _raw_from_files(files: dict[str, tuple[bytes, str]]) -> BasesRaw:
    def read(tipo: str) -> pd.DataFrame:
        conteudo, nome = files.get(tipo, (b"", ""))
        return ler_base_bytes(tipo, conteudo, nome)

    return BasesRaw(
        bussola=read("bussola"),
        painel=read("painel"),
        acoes=read("acoes"),
        produtos_mix=read("produtos_mix"),
        mercado_farma=read("mercado_farma"),
        produtos_mercado_farma=read("produtos_mercado_farma"),
        bussola_historico=read("bussola_historico"),
    )


def _ensure_storage_bucket(client: Any) -> None:
    try:
        client.storage.get_bucket(BUCKET_NAME)
        return
    except Exception:
        pass
    try:
        client.storage.create_bucket(BUCKET_NAME, options={"public": False})
    except Exception as exc:
        if "already" not in str(exc).lower():
            raise


def _auth_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=401, detail=str(exc))


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/dashboard")
@app.get("/api/dashboard", include_in_schema=False)
def dashboard(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return _empty_dashboard(
            message="Supabase nao configurado. Verifique as variaveis de ambiente.",
            supabase_connected=False,
        )

    try:
        context = resolve_user_context(authorization, required=False, empresa_id_override=x_empresa_id)
        client = get_supabase_client()
        empresa_id = context.empresa_id if context else None
        if context is None:
            return _empty_dashboard(supabase_connected=True)
        if context.is_admin_master and not empresa_id:
            empresa_id = get_default_empresa_id()

        rows = _active_base_rows(client, empresa_id)
        bases = _base_statuses(rows)
        if not rows:
            return _empty_dashboard(supabase_connected=True, bases=bases)

        files = _download_active_files(client, rows)
        if "bussola" not in files or "painel" not in files:
            return _empty_dashboard(
                message="Nenhuma base importada ainda",
                supabase_connected=True,
                bases=bases,
            )

        dados = tratar_bases(_raw_from_files(files))
        vendas = dados["vendas"]
        clientes = dados["clientes"]
        indicadores = calcular_indicadores(vendas, clientes)
        resumo = calcular_resumo_operacional(vendas, clientes)
        return jsonable_encoder(
            {
                "ok": True,
                "empty": False,
                "available": True,
                "api_connected": True,
                "supabase_connected": True,
                "message": "API conectada",
                "indicadores": indicadores,
                "resumo": resumo,
                "resumo_operacional": resumo,
                "dados": _records(gerar_resultado_consultor(vendas, clientes), limit=100),
                "bases": bases,
                "avisos": dados.get("avisos", []),
            }
        )
    except SupabaseConfigError:
        return _empty_dashboard(
            message="Supabase nao configurado. Verifique as variaveis de ambiente.",
            supabase_connected=False,
        )
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.get("/consultores")
def consultores() -> Any:
    try:
        dados = _load_local_data()
        resultado = gerar_resultado_consultor(dados["vendas"], dados["clientes"])
        return {"ok": True, "available": True, "consultores": _records(resultado)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/clientes")
def clientes() -> Any:
    try:
        dados = _load_local_data()
        resultado = gerar_resultado_cliente(dados["vendas"], dados["clientes"])
        return {"ok": True, "available": True, "clientes": _records(resultado)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/mercado-farma")
def mercado_farma() -> Any:
    try:
        dados = _load_local_data()
        mercado = preparar_mercado_farma(dados["mercado_farma"])
        melhores = melhor_preco_por_ean(mercado)
        return {"ok": True, "available": True, "melhores_precos": _records(melhores)}
    except Exception as exc:
        return _unavailable(exc)


@app.get("/templates")
@app.get("/api/templates", include_in_schema=False)
def templates() -> dict[str, Any]:
    return {
        "templates": {
            "bussola": COLUNAS_BUSSOLA,
            "painel": COLUNAS_PAINEL,
            "acoes": COLUNAS_ACOES,
            "produtos_mix": COLUNAS_PRODUTOS_MIX,
        }
    }


@app.post("/importacao")
@app.post("/api/importacao", include_in_schema=False)
async def importacao(
    tipo_base: str = Form(...),
    arquivo: UploadFile = File(...),
    ano_mes: str | None = Form(default=None),
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    if tipo_base not in TIPOS_BASE:
        raise HTTPException(status_code=400, detail="tipo_base invalido.")
    filename = _safe_filename(arquivo.filename or "")
    extensao = _extension(filename)
    if extensao not in EXTENSOES_VALIDAS:
        raise HTTPException(status_code=400, detail="Arquivo invalido. Envie .xlsx, .xls ou .csv.")

    try:
        context = resolve_user_context(authorization, required=True, empresa_id_override=x_empresa_id)
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    if context is None or not context.empresa_id:
        raise HTTPException(status_code=403, detail="Usuario sem empresa para importar bases.")

    conteudo = await arquivo.read()
    valido, erro = validar_upload_generico(tipo_base, conteudo, filename)
    if not valido:
        raise HTTPException(status_code=400, detail=erro)

    bruto = ler_base_bytes(tipo_base, conteudo, filename)
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    periodo = ano_mes or datetime.utcnow().strftime("%Y-%m")
    storage_path = f"{context.empresa_id}/{tipo_base}/{periodo}/{uuid4().hex}-{filename}"

    client = get_supabase_client()
    _ensure_storage_bucket(client)
    client.storage.from_(BUCKET_NAME).upload(
        storage_path,
        conteudo,
        file_options={
            "content-type": _content_type(filename, arquivo.content_type),
            "upsert": "false",
        },
    )

    client.table("painel_bases").update({"ativo": False}).eq("empresa_id", context.empresa_id).eq("tipo_base", tipo_base).eq("ativo", True).execute()
    insert_response = (
        client.table("painel_bases")
        .insert(
            {
                "empresa_id": context.empresa_id,
                "tipo_base": tipo_base,
                "nome_arquivo": filename,
                "storage_path": storage_path,
                "linhas": int(bruto.shape[0]),
                "colunas": int(bruto.shape[1]),
                "hash_arquivo": hash_arquivo,
                "ativo": True,
                "uploaded_by": context.user_id,
            }
        )
        .execute()
    )

    return {
        "ok": True,
        "message": "Base importada com sucesso.",
        "base": insert_response.data[0] if isinstance(insert_response.data, list) and insert_response.data else None,
    }


@app.get("/sip")
def sip_status() -> dict[str, Any]:
    return {
        "ok": True,
        "available": False,
        "message": "Nenhuma base importada ainda",
    }


@app.post("/sip")
def sip_create() -> None:
    raise HTTPException(status_code=501, detail="Cadastro de SIP sera persistido em painel_sips.")


@app.get("/foco-semanal")
def foco_semanal_status() -> dict[str, Any]:
    return {"ok": True, "available": False, "message": "Nenhuma base importada ainda"}


@app.post("/foco-semanal")
def foco_semanal_create() -> None:
    raise HTTPException(status_code=501, detail="Persistencia via painel_foco_semanal.")


@app.get("/exportar")
def exportar() -> None:
    raise HTTPException(status_code=501, detail="Exportacao Excel sera gerada a partir das tabelas da API.")
