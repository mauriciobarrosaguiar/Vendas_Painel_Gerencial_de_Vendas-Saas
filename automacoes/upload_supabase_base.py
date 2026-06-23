from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.loader_core import ler_base_bytes, validar_upload_generico
from supabase import create_client


BUCKET_NAME = "painel-bases"


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if value in {'""', "''"}:
        return ""
    return value


def _load_env_file(path: str) -> None:
    if not path:
        return
    env_path = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Arquivo env nao encontrado: {env_path}")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(name.strip(), value)


def _supabase_url() -> str:
    return _env("SUPABASE_URL") or _env("NEXT_PUBLIC_SUPABASE_URL")


def _safe_filename(filename: str) -> str:
    name = Path(filename or "base").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "base.xlsx"


def _content_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _client():
    url = _supabase_url()
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL ou NEXT_PUBLIC_SUPABASE_URL nao configurado.")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY nao configurado.")
    return create_client(url, key)


def _resolve_empresa_id(client, empresa_id: str, empresa_slug: str) -> str:
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
    raise RuntimeError("Nao encontrei empresa ativa para registrar a base.")


def _ensure_bucket(client, bucket_name: str) -> None:
    try:
        client.storage.get_bucket(bucket_name)
        return
    except Exception:
        pass
    try:
        client.storage.create_bucket(bucket_name, options={"public": False})
    except Exception as exc:
        if "already" not in str(exc).lower():
            raise


def upload_base(tipo_base: str, arquivo: Path, nome_arquivo: str, empresa_id: str, empresa_slug: str, bucket_name: str) -> dict:
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {arquivo}")
    filename = _safe_filename(nome_arquivo or arquivo.name)
    conteudo = arquivo.read_bytes()
    valido, erro = validar_upload_generico(tipo_base, conteudo, filename)
    if not valido:
        raise RuntimeError(erro)

    bruto = ler_base_bytes(tipo_base, conteudo, filename)
    client = _client()
    empresa = _resolve_empresa_id(client, empresa_id, empresa_slug)
    _ensure_bucket(client, bucket_name)

    periodo = datetime.utcnow().strftime("%Y-%m")
    storage_path = f"{empresa}/{tipo_base}/{periodo}/{uuid4().hex}-{filename}"
    client.storage.from_(bucket_name).upload(
        storage_path,
        conteudo,
        file_options={"content-type": _content_type(filename), "upsert": "false"},
    )
    client.table("painel_bases").update({"ativo": False}).eq("empresa_id", empresa).eq("tipo_base", tipo_base).eq("ativo", True).execute()
    response = (
        client.table("painel_bases")
        .insert(
            {
                "empresa_id": empresa,
                "tipo_base": tipo_base,
                "nome_arquivo": filename,
                "storage_path": storage_path,
                "linhas": int(bruto.shape[0]),
                "colunas": int(bruto.shape[1]),
                "hash_arquivo": hashlib.sha256(conteudo).hexdigest(),
                "ativo": True,
            }
        )
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else {"storage_path": storage_path, "empresa_id": empresa}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica uma base gerada no Supabase Storage.")
    parser.add_argument("--tipo-base", required=True)
    parser.add_argument("--arquivo", required=True)
    parser.add_argument("--nome-arquivo", default="")
    parser.add_argument("--empresa-id", default=_env("SUPABASE_EMPRESA_ID"))
    parser.add_argument("--empresa-slug", default=_env("SUPABASE_EMPRESA_SLUG", "equipe-norte"))
    parser.add_argument("--bucket", default=_env("SUPABASE_BUCKET", BUCKET_NAME))
    parser.add_argument("--env-file", default="")
    args = parser.parse_args()
    _load_env_file(args.env_file)

    row = upload_base(
        args.tipo_base,
        ROOT / args.arquivo if not Path(args.arquivo).is_absolute() else Path(args.arquivo),
        args.nome_arquivo,
        args.empresa_id or _env("SUPABASE_EMPRESA_ID"),
        args.empresa_slug or _env("SUPABASE_EMPRESA_SLUG", "equipe-norte"),
        args.bucket or _env("SUPABASE_BUCKET", BUCKET_NAME),
    )
    print(f"Base {args.tipo_base} publicada no Supabase: {row.get('storage_path', '')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
