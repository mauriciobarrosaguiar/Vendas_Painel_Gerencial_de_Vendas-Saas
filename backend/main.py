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
from pydantic import BaseModel, Field

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
    from backend.core.mercado_farma import (
        VALID_UFS,
        melhor_preco_por_ean,
        obter_eans_para_consulta,
        preparar_mercado_farma,
        ufs_validas_clientes,
    )
    from backend.core.tratamento import (
        COLUNAS_ACOES,
        COLUNAS_BUSSOLA,
        COLUNAS_PAINEL,
        COLUNAS_PRODUTOS_MIX,
        preparar_painel_equipe,
    )
    from backend.services.github_actions import (
        GitHubActionsConfigError,
        dispatch_workflow,
        is_configured as github_actions_configured,
        list_workflow_runs,
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
    from core.mercado_farma import (
        VALID_UFS,
        melhor_preco_por_ean,
        obter_eans_para_consulta,
        preparar_mercado_farma,
        ufs_validas_clientes,
    )
    from core.tratamento import (
        COLUNAS_ACOES,
        COLUNAS_BUSSOLA,
        COLUNAS_PAINEL,
        COLUNAS_PRODUTOS_MIX,
        preparar_painel_equipe,
    )
    from services.github_actions import (
        GitHubActionsConfigError,
        dispatch_workflow,
        is_configured as github_actions_configured,
        list_workflow_runs,
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
WORKFLOW_BUSSOLA = "bussola.yml"
WORKFLOW_MERCADO_FARMA = "mercadofarma.yml"


class BussolaAutomationRequest(BaseModel):
    headless: bool = True


class MercadoFarmaAutomationRequest(BaseModel):
    ufs: list[str] = Field(default_factory=list)
    todas_ufs: bool = False
    limite_eans: int = Field(default=0, ge=0)
    headless: bool = True


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


def _require_context(authorization: str | None, x_empresa_id: str | None) -> Any:
    try:
        context = resolve_user_context(authorization, required=True, empresa_id_override=x_empresa_id)
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    if context is None or not context.empresa_id:
        raise HTTPException(status_code=403, detail="Usuario sem empresa vinculada.")
    return context


def _normalize_ufs(ufs: list[str]) -> list[str]:
    normalized: list[str] = []
    invalid: list[str] = []
    for item in ufs:
        for piece in str(item or "").replace(";", ",").split(","):
            uf = piece.strip().upper()
            if not uf:
                continue
            if uf not in VALID_UFS:
                invalid.append(uf)
                continue
            if uf not in normalized:
                normalized.append(uf)
    if invalid:
        raise HTTPException(status_code=400, detail="UF invalida: " + ", ".join(sorted(set(invalid))))
    return normalized


def _automation_context(client: Any, empresa_id: str) -> dict[str, Any]:
    rows = _active_base_rows(client, empresa_id)
    files = _download_active_files(client, rows)
    bases = _base_statuses(rows)
    raw = _raw_from_files(files)
    clientes = preparar_painel_equipe(raw.painel) if not raw.painel.empty else pd.DataFrame()
    ufs = ufs_validas_clientes(clientes)
    eans = obter_eans_para_consulta(raw.produtos_mercado_farma)
    return {
        "bases": bases,
        "ufs": ufs,
        "total_eans": len(eans),
        "tem_painel": "painel" in files,
        "tem_produtos_mercado": "produtos_mercado_farma" in files,
    }


def _run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(run.get("id") or ""),
        "name": str(run.get("name") or ""),
        "status": str(run.get("status") or ""),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "run_started_at": run.get("run_started_at"),
        "html_url": run.get("html_url"),
    }


def _safe_runs(workflow: str, limit: int = 5) -> tuple[list[dict[str, Any]], str]:
    if not github_actions_configured():
        return [], "GITHUB_TOKEN/GITHUB_REPO nao configurados."
    try:
        return [_run_summary(run) for run in list_workflow_runs(workflow, limit=limit)], ""
    except GitHubActionsConfigError as exc:
        return [], str(exc)
    except Exception as exc:
        return [], str(exc)


def _register_extraction(
    client: Any,
    empresa_id: str,
    tipo: str,
    parametros: dict[str, Any],
    resultado: dict[str, Any],
) -> None:
    try:
        client.table("painel_extracoes").insert(
            {
                "empresa_id": empresa_id,
                "tipo": tipo,
                "status": "disparado",
                "parametros": parametros,
                "resultado": resultado,
            }
        ).execute()
    except Exception:
        pass


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


@app.get("/automacoes/mercado-farma")
@app.get("/api/automacoes/mercado-farma", include_in_schema=False)
def automacao_mercado_farma_status(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    context = _require_context(authorization, x_empresa_id)
    client = get_supabase_client()
    ctx = _automation_context(client, context.empresa_id)
    runs, runs_error = _safe_runs(WORKFLOW_MERCADO_FARMA)
    return {
        "ok": True,
        "github_configured": github_actions_configured(),
        "available_ufs": ctx["ufs"],
        "total_eans": ctx["total_eans"],
        "tem_painel": ctx["tem_painel"],
        "tem_produtos_mercado": ctx["tem_produtos_mercado"],
        "bases": ctx["bases"],
        "runs": runs,
        "runs_error": runs_error,
    }


@app.post("/automacoes/mercado-farma")
@app.post("/api/automacoes/mercado-farma", include_in_schema=False)
def automacao_mercado_farma_disparar(
    payload: MercadoFarmaAutomationRequest,
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    context = _require_context(authorization, x_empresa_id)
    client = get_supabase_client()
    ctx = _automation_context(client, context.empresa_id)
    available_ufs = list(ctx["ufs"])
    selected_ufs = available_ufs if payload.todas_ufs else _normalize_ufs(payload.ufs)
    if not selected_ufs:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma UF com cliente ativo.")

    unavailable = [uf for uf in selected_ufs if uf not in available_ufs]
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail="UF sem cliente ativo/CNPJ referencia na base atual: " + ", ".join(unavailable),
        )
    if not ctx["tem_produtos_mercado"]:
        raise HTTPException(status_code=400, detail="Importe Produtos Mercado Farma antes de atualizar os precos.")

    command_id = uuid4().hex
    inputs = {
        "acao": "atualizar_mercadofarma_paralelo",
        "ufs": ",".join(selected_ufs),
        "uf": ",".join(selected_ufs),
        "limite_eans": str(max(payload.limite_eans, 0)),
        "headless": "true" if payload.headless else "false",
        "empresa_id": context.empresa_id,
        "command_id": command_id,
    }
    try:
        dispatch = dispatch_workflow(WORKFLOW_MERCADO_FARMA, inputs)
    except GitHubActionsConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    _register_extraction(
        client,
        context.empresa_id,
        "mercado_farma",
        {"ufs": selected_ufs, "limite_eans": payload.limite_eans, "headless": payload.headless},
        {"workflow": WORKFLOW_MERCADO_FARMA, "command_id": command_id},
    )
    return {
        "ok": True,
        "message": "Atualizacao Mercado Farma disparada no GitHub Actions.",
        "workflow": dispatch["workflow"],
        "branch": dispatch["branch"],
        "ufs": selected_ufs,
        "command_id": command_id,
    }


@app.get("/automacoes/bussola")
@app.get("/api/automacoes/bussola", include_in_schema=False)
def automacao_bussola_status(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_context(authorization, x_empresa_id)
    runs, runs_error = _safe_runs(WORKFLOW_BUSSOLA)
    return {
        "ok": True,
        "github_configured": github_actions_configured(),
        "runs": runs,
        "runs_error": runs_error,
    }


@app.post("/automacoes/bussola")
@app.post("/api/automacoes/bussola", include_in_schema=False)
def automacao_bussola_disparar(
    payload: BussolaAutomationRequest,
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    context = _require_context(authorization, x_empresa_id)
    client = get_supabase_client()
    command_id = uuid4().hex
    inputs = {
        "acao": "extrair_bussola",
        "headless": "true" if payload.headless else "false",
        "empresa_id": context.empresa_id,
        "command_id": command_id,
    }
    try:
        dispatch = dispatch_workflow(WORKFLOW_BUSSOLA, inputs)
    except GitHubActionsConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    _register_extraction(
        client,
        context.empresa_id,
        "bussola",
        {"headless": payload.headless},
        {"workflow": WORKFLOW_BUSSOLA, "command_id": command_id},
    )
    return {
        "ok": True,
        "message": "Extracao Bussola disparada no GitHub Actions.",
        "workflow": dispatch["workflow"],
        "branch": dispatch["branch"],
        "command_id": command_id,
    }


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
