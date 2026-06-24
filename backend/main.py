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
        gerar_resultado_produto,
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
        normalizar_cnpj,
        preparar_painel_equipe,
        preparar_produtos_mix,
    )
    from backend.services.github_actions import (
        GitHubActionsConfigError,
        dispatch_workflow,
        is_configured as github_actions_configured,
        list_workflow_runs,
    )
    from backend.services.automation_credentials import (
        CredentialsConfigError,
        credentials_available,
        load_credentials,
        mask_user,
        save_credentials,
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
        gerar_resultado_produto,
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
        normalizar_cnpj,
        preparar_painel_equipe,
        preparar_produtos_mix,
    )
    from services.github_actions import (
        GitHubActionsConfigError,
        dispatch_workflow,
        is_configured as github_actions_configured,
        list_workflow_runs,
    )
    from services.automation_credentials import (
        CredentialsConfigError,
        credentials_available,
        load_credentials,
        mask_user,
        save_credentials,
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
    "bussola_historico": "Historico Bussola",
}
TIPO_BASE_ALIASES = {"produtos_mercado_farma": "produtos_mix"}
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


class BussolaCredentialsRequest(BaseModel):
    gd_usuario: str = ""
    gd_senha: str = ""
    usar_gd: bool = True
    headless: bool = True


class MercadoFarmaCredentialsRequest(BaseModel):
    usuario: str = ""
    senha: str = ""


class AutomationCredentialsRequest(BaseModel):
    bussola: BussolaCredentialsRequest | None = None
    mercado_farma: MercadoFarmaCredentialsRequest | None = None


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


def _active_company_files(
    authorization: str | None,
    x_empresa_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, tuple[bytes, str]]]:
    context = resolve_user_context(authorization, required=False, empresa_id_override=x_empresa_id)
    client = get_supabase_client()
    empresa_id = context.empresa_id if context else None
    if context and context.is_admin_master and not empresa_id:
        empresa_id = get_default_empresa_id()
    if not empresa_id:
        return _base_statuses([]), {}

    rows = _active_base_rows(client, empresa_id)
    bases = _base_statuses(rows)
    try:
        return bases, _download_active_files(client, rows)
    except Exception:
        return bases, {}


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


def _vendedores_gd_summary(clientes: pd.DataFrame) -> list[dict[str, Any]]:
    if clientes is None or clientes.empty:
        return []
    base = clientes.copy()
    for coluna in ["nome_gd", "setor_rep", "nome_rep", "uf", "cnpj_limpo", "cnpj", "cliente_ativo"]:
        if coluna not in base.columns:
            base[coluna] = ""
    if "cliente_ativo" in base.columns:
        base = base[base["cliente_ativo"].fillna(True)].copy()
    base["cnpj_resumo"] = base["cnpj_limpo"].where(base["cnpj_limpo"].astype(str).str.strip().ne(""), base["cnpj"])
    base["cnpj_resumo"] = base["cnpj_resumo"].apply(normalizar_cnpj)
    base = base[base["cnpj_resumo"].astype(str).str.len().eq(14)].copy()
    if base.empty:
        return []

    for coluna in ["nome_gd", "setor_rep", "nome_rep", "uf"]:
        base[coluna] = base[coluna].fillna("").astype(str).str.strip()
    base["nome_gd"] = base["nome_gd"].replace("", "SEM GD")
    base["setor_rep"] = base["setor_rep"].replace("", "SEM SETOR")
    base["nome_rep"] = base["nome_rep"].replace("", "SEM VENDEDOR")
    base["uf"] = base["uf"].str.upper()

    totais = (
        base.groupby("nome_gd", dropna=False)
        .agg(total_vendedores_gd=("nome_rep", "nunique"), total_clientes_gd=("cnpj_resumo", "nunique"))
        .to_dict("index")
    )
    linhas: list[dict[str, Any]] = []
    agrupado = base.groupby(["nome_gd", "setor_rep", "nome_rep"], dropna=False)
    for (gd, setor, vendedor), grupo in agrupado:
        ufs = sorted({str(uf).strip().upper() for uf in grupo["uf"].dropna().tolist() if str(uf).strip()})
        total_gd = totais.get(str(gd), {})
        linhas.append(
            {
                "gd": str(gd),
                "setor": str(setor),
                "vendedor": str(vendedor),
                "ufs": ufs,
                "clientes_ativos": int(grupo["cnpj_resumo"].nunique()),
                "total_vendedores_gd": int(total_gd.get("total_vendedores_gd", 0) or 0),
                "total_clientes_gd": int(total_gd.get("total_clientes_gd", 0) or 0),
            }
        )
    return sorted(linhas, key=lambda item: (item["gd"], item["setor"], item["vendedor"]))


def _enrich_mercado_with_clients(mercado: pd.DataFrame, clientes: pd.DataFrame) -> pd.DataFrame:
    if mercado is None or mercado.empty:
        return mercado.copy() if mercado is not None else pd.DataFrame()
    base = mercado.copy()
    for coluna in ["nome_gd", "setor_rep", "nome_rep", "vinculo_painel"]:
        if coluna not in base.columns:
            base[coluna] = ""
    if clientes is None or clientes.empty:
        base["vinculo_painel"] = "Sem vinculo no Painel clientes"
        return base

    painel = clientes.copy()
    for coluna in ["cnpj_limpo", "cnpj", "nome_gd", "setor_rep", "nome_rep", "uf"]:
        if coluna not in painel.columns:
            painel[coluna] = ""
    painel["cnpj_chave"] = painel["cnpj_limpo"].where(
        painel["cnpj_limpo"].astype(str).str.strip().ne(""),
        painel["cnpj"],
    ).apply(normalizar_cnpj)
    painel = painel[painel["cnpj_chave"].astype(str).str.len().eq(14)].drop_duplicates("cnpj_chave")
    if painel.empty:
        base["vinculo_painel"] = "Sem vinculo no Painel clientes"
        return base

    mapa = painel.set_index("cnpj_chave")[["nome_gd", "setor_rep", "nome_rep", "uf"]]
    chave = base["cnpj_referencia"].apply(normalizar_cnpj) if "cnpj_referencia" in base.columns else pd.Series("", index=base.index)
    for coluna in ["nome_gd", "setor_rep", "nome_rep"]:
        base[coluna] = chave.map(mapa[coluna]).fillna("")
    uf_painel = chave.map(mapa["uf"]).fillna("")
    if "uf" in base.columns:
        base["uf"] = base["uf"].where(base["uf"].astype(str).str.strip().ne(""), uf_painel)
    sem_vinculo = base[["nome_gd", "setor_rep", "nome_rep"]].fillna("").astype(str).eq("").all(axis=1)
    base.loc[sem_vinculo, "vinculo_painel"] = "Sem vinculo no Painel clientes"
    base.loc[~sem_vinculo, "vinculo_painel"] = "Painel clientes"
    return base


def _automation_context(client: Any, empresa_id: str) -> dict[str, Any]:
    rows = _active_base_rows(client, empresa_id)
    try:
        files = _download_active_files(client, rows)
    except Exception:
        files = {}
    bases = _base_statuses(rows)
    raw = _raw_from_files(files)
    clientes = preparar_painel_equipe(raw.painel) if not raw.painel.empty else pd.DataFrame()
    ufs = ufs_validas_clientes(clientes)
    eans = obter_eans_para_consulta(raw.produtos_mix)
    return {
        "bases": bases,
        "ufs": ufs,
        "total_eans": len(eans),
        "tem_painel": "painel" in files,
        "tem_produtos_mix": "produtos_mix" in files,
        "tem_produtos_mercado": "produtos_mix" in files,
        "vendedores_gd": _vendedores_gd_summary(clientes),
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


def _merge_bussola_credentials(current: dict[str, Any], payload: BussolaCredentialsRequest) -> dict[str, Any]:
    gd_current = current.get("gd", {}) if isinstance(current.get("gd"), dict) else {}
    gd_usuario = payload.gd_usuario.strip() or str(gd_current.get("usuario", "") or "")
    gd_senha = payload.gd_senha.strip() or str(gd_current.get("senha", "") or "")
    return {
        "gd": {
            "usuario": gd_usuario,
            "senha": gd_senha,
            "usar_gd": bool(payload.usar_gd),
        },
        "consultores": current.get("consultores", {}) if isinstance(current.get("consultores"), dict) else {},
        "headless": bool(payload.headless),
    }


def _merge_mercado_credentials(current: dict[str, Any], payload: MercadoFarmaCredentialsRequest) -> dict[str, Any]:
    return {
        "usuario": payload.usuario.strip() or str(current.get("usuario", "") or ""),
        "senha": payload.senha.strip() or str(current.get("senha", "") or ""),
    }


def _credentials_summary(client: Any, empresa_id: str) -> dict[str, Any]:
    try:
        bussola = load_credentials(client, empresa_id, "bussola")
        mercado = load_credentials(client, empresa_id, "mercado_farma")
    except CredentialsConfigError:
        bussola = {}
        mercado = {}
    gd = bussola.get("gd", {}) if isinstance(bussola.get("gd"), dict) else {}
    return {
        "ok": True,
        "encryption_configured": credentials_available(),
        "bussola": {
            "gd_usuario": str(gd.get("usuario", "") or ""),
            "gd_usuario_mascarado": mask_user(gd.get("usuario", "")),
            "tem_senha": bool(gd.get("senha")),
            "usar_gd": bool(gd.get("usar_gd", True)),
            "headless": bool(bussola.get("headless", True)),
        },
        "mercado_farma": {
            "usuario": str(mercado.get("usuario", "") or ""),
            "usuario_mascarado": mask_user(mercado.get("usuario", "")),
            "tem_senha": bool(mercado.get("senha")),
        },
    }


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
        bases, files = _active_company_files(authorization, x_empresa_id)
        if not files:
            return _empty_dashboard(supabase_connected=True, bases=bases)

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
        "tem_produtos_mix": ctx["tem_produtos_mix"],
        "tem_produtos_mercado": ctx["tem_produtos_mercado"],
        "vendedores_gd": ctx["vendedores_gd"],
        "bases": ctx["bases"],
        "runs": runs,
        "runs_error": runs_error,
    }


@app.get("/automacoes/credenciais")
@app.get("/api/automacoes/credenciais", include_in_schema=False)
def automacao_credenciais_status(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    context = _require_context(authorization, x_empresa_id)
    client = get_supabase_client()
    return _credentials_summary(client, context.empresa_id)


@app.post("/automacoes/credenciais")
@app.post("/api/automacoes/credenciais", include_in_schema=False)
def automacao_credenciais_salvar(
    payload: AutomationCredentialsRequest,
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    context = _require_context(authorization, x_empresa_id)
    client = get_supabase_client()
    if not credentials_available():
        raise HTTPException(status_code=503, detail="Configure PERSISTENCE_KEY para salvar credenciais.")

    try:
        if payload.bussola is not None:
            current = load_credentials(client, context.empresa_id, "bussola")
            merged = _merge_bussola_credentials(current, payload.bussola)
            save_credentials(client, context.empresa_id, "bussola", merged, user_id=context.user_id)
        if payload.mercado_farma is not None:
            current = load_credentials(client, context.empresa_id, "mercado_farma")
            merged = _merge_mercado_credentials(current, payload.mercado_farma)
            save_credentials(client, context.empresa_id, "mercado_farma", merged, user_id=context.user_id)
    except CredentialsConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {**_credentials_summary(client, context.empresa_id), "message": "Credenciais salvas com seguranca."}


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
    if not ctx["tem_painel"]:
        raise HTTPException(status_code=400, detail="Importe Painel clientes para listar UFs.")
    if not ctx["tem_produtos_mix"] or int(ctx["total_eans"] or 0) <= 0:
        raise HTTPException(status_code=400, detail="Importe Produtos / Mix para gerar lista de EANs.")
    selected_ufs = available_ufs if payload.todas_ufs else _normalize_ufs(payload.ufs)
    if not selected_ufs:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma UF com cliente ativo.")

    unavailable = [uf for uf in selected_ufs if uf not in available_ufs]
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail="UF sem cliente ativo/CNPJ referencia na base atual: " + ", ".join(unavailable),
        )

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
@app.get("/api/consultores", include_in_schema=False)
def consultores(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return _empty_dashboard(message="Supabase nao configurado. Verifique as variaveis de ambiente.")
    try:
        bases, files = _active_company_files(authorization, x_empresa_id)
        if "bussola" not in files or "painel" not in files:
            return {"ok": True, "available": False, "message": "Nenhuma base importada ainda", "consultores": [], "bases": bases}
        dados = tratar_bases(_raw_from_files(files))
        resultado = gerar_resultado_consultor(dados["vendas"], dados["clientes"])
        return {"ok": True, "available": True, "consultores": _records(resultado), "bases": bases}
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.get("/clientes")
@app.get("/api/clientes", include_in_schema=False)
def clientes(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return _empty_dashboard(message="Supabase nao configurado. Verifique as variaveis de ambiente.")
    try:
        bases, files = _active_company_files(authorization, x_empresa_id)
        if "bussola" not in files or "painel" not in files:
            return {"ok": True, "available": False, "message": "Nenhuma base importada ainda", "clientes": [], "bases": bases}
        dados = tratar_bases(_raw_from_files(files))
        resultado = gerar_resultado_cliente(dados["vendas"], dados["clientes"])
        return {"ok": True, "available": True, "clientes": _records(resultado), "bases": bases}
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.get("/mercado-farma")
@app.get("/api/mercado-farma", include_in_schema=False)
def mercado_farma(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return _empty_dashboard(message="Supabase nao configurado. Verifique as variaveis de ambiente.")
    try:
        bases, files = _active_company_files(authorization, x_empresa_id)
        if "mercado_farma" not in files:
            return {"ok": True, "available": False, "message": "Nenhuma base importada ainda", "melhores_precos": [], "bases": bases}
        raw = _raw_from_files(files)
        mercado = preparar_mercado_farma(raw.mercado_farma)
        clientes = preparar_painel_equipe(raw.painel) if "painel" in files else pd.DataFrame()
        mercado = _enrich_mercado_with_clients(mercado, clientes)
        melhores = melhor_preco_por_ean(mercado)
        melhores = _enrich_mercado_with_clients(melhores, clientes)
        return {"ok": True, "available": True, "melhores_precos": _records(melhores), "bases": bases}
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.get("/templates")
@app.get("/api/templates", include_in_schema=False)
def templates() -> dict[str, Any]:
    return {
        "ok": True,
        "modelos": [
            {"modelo": "Bussola", "arquivo": "modelo_bussola.xlsx", "aba": "Pedidos", "download": "/modelos/modelo_bussola.xlsx"},
            {"modelo": "Painel clientes", "arquivo": "modelo_painel_clientes.xlsx", "aba": "Planilha1", "download": "/modelos/modelo_painel_clientes.xlsx"},
            {"modelo": "Produtos / Mix", "arquivo": "modelo_produtos_mix.xlsx", "aba": "Produtos", "download": "/modelos/modelo_produtos_mix.xlsx"},
            {"modelo": "Acoes promocionais", "arquivo": "modelo_acoes_promocionais.xlsx", "aba": "Acoes", "download": "/modelos/modelo_acoes_promocionais.xlsx"},
            {"modelo": "Mercado Farma", "arquivo": "modelo_mercado_farma.xlsx", "aba": "Mercado Farma", "download": "/modelos/modelo_mercado_farma.xlsx"},
            {"modelo": "Historico Bussola", "arquivo": "modelo_bussola_historico.xlsx", "aba": "Pedidos", "download": "/modelos/modelo_bussola_historico.xlsx"},
        ],
        "templates": {
            "bussola": COLUNAS_BUSSOLA,
            "painel": COLUNAS_PAINEL,
            "acoes": COLUNAS_ACOES,
            "produtos_mix": COLUNAS_PRODUTOS_MIX,
        }
    }


@app.get("/produtos-mix")
@app.get("/api/produtos-mix", include_in_schema=False)
def produtos_mix_status(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return {"ok": True, "available": False, "message": "Supabase nao configurado.", "produtos": [], "bases": _base_statuses([])}
    try:
        bases, files = _active_company_files(authorization, x_empresa_id)
        if "produtos_mix" not in files:
            return {"ok": True, "available": False, "message": "Nenhuma base Produtos / Mix importada ainda.", "produtos": [], "bases": bases}
        raw = _raw_from_files(files)
        produtos = preparar_produtos_mix(raw.produtos_mix)
        if "bussola" in files and "painel" in files:
            dados = tratar_bases(raw)
            resultado = gerar_resultado_produto(dados["vendas"], dados["produtos_mix"])
        else:
            resultado = produtos.rename(columns={"ean": "ean_mix"}).copy()
            resultado["ean"] = resultado.get("ean_limpo", resultado.get("ean_mix", ""))
            resultado["ol_total"] = 0
            resultado["quantidade_vendida"] = 0
            resultado["clientes_compradores"] = 0
            resultado["consultores_que_venderam"] = ""
            resultado = resultado[["ean", "produto", "tipo_mix", "ol_total", "quantidade_vendida", "clientes_compradores", "consultores_que_venderam"]]
        rows = []
        for item in _records(resultado, limit=300):
            rows.append(
                {
                    "EAN": item.get("ean", ""),
                    "Produto": item.get("produto", ""),
                    "Tipo mix": item.get("tipo_mix", ""),
                    "OL sem combate": item.get("ol_total", 0),
                    "Quantidade": item.get("quantidade_vendida", 0),
                    "Clientes": item.get("clientes_compradores", 0),
                }
            )
        return {
            "ok": True,
            "available": True,
            "message": "Produtos / Mix carregado.",
            "total_produtos": int(len(produtos)),
            "produtos": rows,
            "bases": bases,
        }
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.get("/importacao")
@app.get("/api/importacao", include_in_schema=False)
def importacao_status(
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> Any:
    if not is_supabase_configured():
        return {
            "ok": True,
            "available": False,
            "message": "Supabase nao configurado.",
            "bases": _base_statuses([]),
            "mercado_farma": {"available_ufs": [], "total_eans": 0, "tem_painel": False, "tem_produtos_mix": False},
            "vendedores_gd": [],
        }
    try:
        context = _require_context(authorization, x_empresa_id)
        client = get_supabase_client()
        ctx = _automation_context(client, context.empresa_id)
        return {
            "ok": True,
            "available": True,
            "message": "Status de importacao carregado.",
            "bases": ctx["bases"],
            "mercado_farma": {
                "available_ufs": ctx["ufs"],
                "total_eans": ctx["total_eans"],
                "tem_painel": ctx["tem_painel"],
                "tem_produtos_mix": ctx["tem_produtos_mix"],
            },
            "vendedores_gd": ctx["vendedores_gd"],
        }
    except PermissionError as exc:
        raise _auth_error(exc) from exc
    except Exception as exc:
        return _unavailable(exc)


@app.post("/importacao")
@app.post("/api/importacao", include_in_schema=False)
async def importacao(
    tipo_base: str = Form(...),
    arquivo: UploadFile = File(...),
    ano_mes: str | None = Form(default=None),
    authorization: str | None = Header(default=None),
    x_empresa_id: str | None = Header(default=None),
) -> dict[str, Any]:
    tipo_base = TIPO_BASE_ALIASES.get(tipo_base, tipo_base)
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

    base_row = insert_response.data[0] if isinstance(insert_response.data, list) and insert_response.data else None
    return {
        "ok": True,
        "message": "Base importada com sucesso.",
        "nome_arquivo": filename,
        "linhas": int(bruto.shape[0]),
        "colunas": int(bruto.shape[1]),
        "created_at": base_row.get("created_at") if isinstance(base_row, dict) else None,
        "base": base_row,
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
