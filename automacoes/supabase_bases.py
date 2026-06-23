from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from backend.core.loader_core import BasesRaw, ler_base_bytes, tratar_bases
from supabase import create_client


BUCKET_NAME = "painel-bases"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def supabase_configured() -> bool:
    return bool((_env("SUPABASE_URL") or _env("NEXT_PUBLIC_SUPABASE_URL")) and _env("SUPABASE_SERVICE_ROLE_KEY"))


def _client():
    url = _env("SUPABASE_URL") or _env("NEXT_PUBLIC_SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL ou NEXT_PUBLIC_SUPABASE_URL nao configurado.")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY nao configurado.")
    return create_client(url, key)


def _resolve_empresa_id(client: Any, empresa_id: str = "", empresa_slug: str = "") -> str:
    if empresa_id:
        return empresa_id
    slug = empresa_slug or _env("SUPABASE_EMPRESA_SLUG", "equipe-norte")
    response = client.table("core_empresas").select("id").eq("slug", slug).eq("ativo", True).limit(1).execute()
    rows = response.data if isinstance(response.data, list) else []
    if rows and rows[0].get("id"):
        return str(rows[0]["id"])
    response = client.table("core_empresas").select("id").eq("ativo", True).limit(1).execute()
    rows = response.data if isinstance(response.data, list) else []
    if rows and rows[0].get("id"):
        return str(rows[0]["id"])
    raise RuntimeError("Nao encontrei empresa ativa no Supabase.")


def _active_rows(client: Any, empresa_id: str) -> list[dict[str, Any]]:
    response = (
        client.table("painel_bases")
        .select("tipo_base,nome_arquivo,storage_path,created_at")
        .eq("empresa_id", empresa_id)
        .eq("ativo", True)
        .order("created_at", desc=True)
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        tipo = str(row.get("tipo_base") or "")
        if tipo and tipo not in latest:
            latest[tipo] = row
    return list(latest.values())


def carregar_dados_tratados_supabase(empresa_id: str = "", empresa_slug: str = "") -> dict[str, Any]:
    client = _client()
    empresa = _resolve_empresa_id(client, empresa_id, empresa_slug)
    bucket = client.storage.from_(BUCKET_NAME)
    arquivos: dict[str, tuple[bytes, str]] = {}
    for row in _active_rows(client, empresa):
        tipo = str(row.get("tipo_base") or "")
        path = str(row.get("storage_path") or "")
        if tipo and path:
            arquivos[tipo] = (bucket.download(path), str(row.get("nome_arquivo") or path))
    if not arquivos:
        raise RuntimeError("Nenhuma base ativa encontrada no Supabase para a empresa.")

    def read(tipo: str) -> pd.DataFrame:
        conteudo, nome = arquivos.get(tipo, (b"", ""))
        return ler_base_bytes(tipo, conteudo, nome)

    return tratar_bases(
        BasesRaw(
            bussola=read("bussola"),
            painel=read("painel"),
            acoes=read("acoes"),
            produtos_mix=read("produtos_mix"),
            mercado_farma=read("mercado_farma"),
            produtos_mercado_farma=read("produtos_mercado_farma"),
            bussola_historico=read("bussola_historico"),
        )
    )
