from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


class SupabaseConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class UserContext:
    user_id: str | None
    email: str
    papel: str
    empresa_id: str | None
    nome: str

    @property
    def is_admin_master(self) -> bool:
        return self.papel == "admin_master"


_client: Any | None = None
_PUBLIC_EMPRESA_ID_FALLBACK = "38795669-3da2-4227-9248-d1c607e54b31"


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def public_panel_mode() -> bool:
    value = _env("PUBLIC_PANEL_MODE")
    if not value:
        return True
    return value.lower() not in {"0", "false", "no", "nao", "não", "off"}


def public_empresa_slug() -> str:
    return _env("PUBLIC_EMPRESA_SLUG") or _env("SUPABASE_EMPRESA_SLUG") or "equipe-norte"


def public_empresa_id() -> str:
    return _env("PUBLIC_EMPRESA_ID") or _env("SUPABASE_EMPRESA_ID") or _env("NEXT_PUBLIC_EMPRESA_ID")


def get_supabase_url() -> str:
    return _env("SUPABASE_URL") or _env("NEXT_PUBLIC_SUPABASE_URL")


def assert_supabase_configured() -> None:
    missing: list[str] = []
    if not get_supabase_url():
        missing.append("SUPABASE_URL ou NEXT_PUBLIC_SUPABASE_URL")
    if not _env("SUPABASE_SERVICE_ROLE_KEY"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise SupabaseConfigError("Variaveis ausentes: " + ", ".join(missing))


def get_supabase_client() -> Any:
    global _client
    if _client is None:
        assert_supabase_configured()
        from supabase import create_client

        _client = create_client(get_supabase_url(), _env("SUPABASE_SERVICE_ROLE_KEY"))
    return _client


def is_supabase_configured() -> bool:
    return bool(get_supabase_url() and _env("SUPABASE_SERVICE_ROLE_KEY"))


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _response_data(response: Any) -> Any:
    return getattr(response, "data", None)


def _first(response: Any) -> dict[str, Any] | None:
    data = _response_data(response)
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def _auth_user_id(user_response: Any) -> tuple[str | None, str]:
    user = getattr(user_response, "user", None)
    if user is None:
        user = _response_data(user_response)
    if isinstance(user, dict):
        return user.get("id"), str(user.get("email") or "")
    return getattr(user, "id", None), str(getattr(user, "email", "") or "")


def get_default_empresa_id(slug: str | None = None) -> str | None:
    """Resolve a empresa padrão.

    Em produção pública na Vercel, chamar o Supabase apenas para descobrir a
    empresa causava erro intermitente de conexão quando a página carregava várias
    APIs ao mesmo tempo. Por isso, usamos primeiro a env SUPABASE_EMPRESA_ID ou
    PUBLIC_EMPRESA_ID. Para este projeto, mantemos também o fallback do seed
    oficial da Equipe Norte.
    """
    env_empresa_id = public_empresa_id()
    if env_empresa_id:
        return env_empresa_id

    slug = (slug or public_empresa_slug()).strip()
    if slug == "equipe-norte":
        return _PUBLIC_EMPRESA_ID_FALLBACK

    client = get_supabase_client()
    if slug:
        try:
            response = client.table("core_empresas").select("id").eq("slug", slug).eq("ativo", True).limit(1).execute()
            row = _first(response)
            if row and row.get("id"):
                return str(row["id"])
        except Exception:
            pass
    response = client.table("core_empresas").select("id").eq("ativo", True).limit(1).execute()
    row = _first(response)
    return str(row["id"]) if row and row.get("id") else None


def resolve_user_context(
    authorization: str | None,
    *,
    required: bool,
    empresa_id_override: str | None = None,
) -> UserContext | None:
    token = bearer_token(authorization)
    if not token:
        if public_panel_mode():
            empresa_id = empresa_id_override or get_default_empresa_id(public_empresa_slug())
            if not empresa_id:
                if required:
                    raise PermissionError("Empresa padrao nao encontrada.")
                return None
            return UserContext(
                user_id=None,
                email="publico@painel.local",
                papel="admin_master",
                empresa_id=empresa_id,
                nome="Acesso Publico",
            )
        if required:
            raise PermissionError("Acesso nao autorizado para esta operacao.")
        return None

    client = get_supabase_client()
    auth_response = client.auth.get_user(token)
    user_id, email = _auth_user_id(auth_response)
    if not user_id:
        raise PermissionError("Token invalido.")

    response = (
        client.table("core_usuarios")
        .select("id,email,nome,papel,empresa_id,ativo")
        .eq("id", user_id)
        .eq("ativo", True)
        .limit(1)
        .execute()
    )
    row = _first(response)
    if not row:
        raise PermissionError("Usuario sem vinculo ativo em core_usuarios.")

    papel = str(row.get("papel") or "")
    empresa_id = str(row["empresa_id"]) if row.get("empresa_id") else None
    if papel == "admin_master" and empresa_id_override:
        empresa_id = empresa_id_override
    if papel == "admin_master" and not empresa_id:
        empresa_id = get_default_empresa_id()
    if papel != "admin_master" and empresa_id_override and empresa_id_override != empresa_id:
        raise PermissionError("Usuario nao pode acessar outra empresa.")
    if papel != "admin_master" and not empresa_id:
        raise PermissionError("Usuario sem empresa vinculada.")

    return UserContext(
        user_id=user_id,
        email=str(row.get("email") or email),
        papel=papel,
        empresa_id=empresa_id,
        nome=str(row.get("nome") or ""),
    )