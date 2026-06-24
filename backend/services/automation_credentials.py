from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from typing import Any

import requests
from cryptography.fernet import Fernet


CREDENTIAL_TYPES = {"bussola", "mercado_farma"}


class CredentialsConfigError(RuntimeError):
    pass


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    if value in {'""', "''"}:
        return ""
    return value


def _safe_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    # Evita mensagens gigantes, mas mantém o suficiente para diagnosticar Vercel/Supabase.
    return text[:800]


def _fernet() -> Fernet:
    key = _env("PERSISTENCE_KEY")
    if not key:
        raise CredentialsConfigError("Configure PERSISTENCE_KEY para salvar credenciais com criptografia.")
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest())
        return Fernet(derived)


def credentials_available() -> bool:
    return bool(_env("PERSISTENCE_KEY"))


def mask_user(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if "@" in text:
        name, domain = text.split("@", 1)
        if len(name) <= 2:
            return f"{name[:1]}***@{domain}"
        return f"{name[:2]}***{name[-1:]}@{domain}"
    if len(text) <= 4:
        return text[:1] + "***"
    return text[:2] + "***" + text[-2:]


def encrypt_payload(payload: dict[str, Any]) -> str:
    content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(content).decode("utf-8")


def decrypt_payload(value: str) -> dict[str, Any]:
    if not value:
        return {}
    content = _fernet().decrypt(value.encode("utf-8"))
    data = json.loads(content.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def credential_tipo(tipo: str) -> str:
    if tipo not in CREDENTIAL_TYPES:
        raise ValueError("Tipo de credencial invalido.")
    return f"credenciais_{tipo}"


def _supabase_url() -> str:
    return (_env("SUPABASE_URL") or _env("NEXT_PUBLIC_SUPABASE_URL")).rstrip("/")


def _service_key() -> str:
    return _env("SUPABASE_SERVICE_ROLE_KEY")


def _rest_headers(*, prefer: str | None = None) -> dict[str, str]:
    token = _service_key()
    if not _supabase_url() or not token:
        raise CredentialsConfigError("Configure NEXT_PUBLIC_SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no Vercel.")
    headers = {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Connection": "close",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None, prefer: str | None = None) -> requests.Response:
    url = f"{_supabase_url()}/rest/v1/{path.lstrip('/')}"
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.request(
                method,
                url,
                headers=_rest_headers(prefer=prefer),
                params=params,
                json=json_body,
                timeout=20,
            )
            if response.status_code >= 400:
                raise CredentialsConfigError(f"Supabase REST HTTP {response.status_code}: {response.text[:500]}")
            return response
        except CredentialsConfigError:
            raise
        except Exception as exc:
            last_exc = exc
            time.sleep(0.4 * (attempt + 1))
    raise CredentialsConfigError("Falha de conexao com Supabase REST: " + _safe_error(last_exc or RuntimeError("erro desconhecido")))


def _load_credentials_rest(empresa_id: str, tipo: str) -> dict[str, Any]:
    response = _rest_request(
        "GET",
        "painel_extracoes",
        params={
            "select": "resultado,created_at",
            "empresa_id": f"eq.{empresa_id}",
            "tipo": f"eq.{credential_tipo(tipo)}",
            "status": "eq.ativo",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    rows = response.json() if response.text else []
    if not isinstance(rows, list) or not rows:
        return {}
    result = rows[0].get("resultado", {}) if isinstance(rows[0], dict) else {}
    encrypted = result.get("payload") if isinstance(result, dict) else ""
    return decrypt_payload(str(encrypted or ""))


def _save_credentials_rest(empresa_id: str, tipo: str, payload: dict[str, Any], *, user_id: str | None = None) -> None:
    tipo_registro = credential_tipo(tipo)
    encrypted = encrypt_payload(payload)
    try:
        _rest_request(
            "PATCH",
            "painel_extracoes",
            params={
                "empresa_id": f"eq.{empresa_id}",
                "tipo": f"eq.{tipo_registro}",
                "status": "eq.ativo",
            },
            json_body={"status": "substituido"},
            prefer="return=minimal",
        )
    except Exception:
        # Se não houver registro anterior, ou se a atualização falhar por algum detalhe temporário,
        # ainda tentamos inserir a nova credencial ativa.
        pass
    _rest_request(
        "POST",
        "painel_extracoes",
        json_body={
            "empresa_id": empresa_id,
            "tipo": tipo_registro,
            "status": "ativo",
            "parametros": {"updated_by": user_id} if user_id else {},
            "resultado": {"payload": encrypted},
        },
        prefer="return=minimal",
    )


def load_credentials(client: Any, empresa_id: str, tipo: str) -> dict[str, Any]:
    try:
        return _load_credentials_rest(empresa_id, tipo)
    except CredentialsConfigError:
        raise
    except Exception as exc:
        # Fallback para ambientes locais antigos que ainda usam o client Python.
        try:
            response = (
                client.table("painel_extracoes")
                .select("resultado,created_at")
                .eq("empresa_id", empresa_id)
                .eq("tipo", credential_tipo(tipo))
                .eq("status", "ativo")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = response.data if isinstance(response.data, list) else []
            if not rows:
                return {}
            result = rows[0].get("resultado", {}) if isinstance(rows[0], dict) else {}
            encrypted = result.get("payload") if isinstance(result, dict) else ""
            return decrypt_payload(str(encrypted or ""))
        except CredentialsConfigError:
            raise
        except Exception as fallback_exc:
            raise CredentialsConfigError(
                "Falha ao ler credenciais no Supabase: " + _safe_error(fallback_exc) + " | REST: " + _safe_error(exc)
            ) from fallback_exc


def save_credentials(
    client: Any,
    empresa_id: str,
    tipo: str,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
    try:
        _save_credentials_rest(empresa_id, tipo, payload, user_id=user_id)
    except CredentialsConfigError:
        raise
    except Exception as exc:
        # Fallback para execução local.
        try:
            tipo_registro = credential_tipo(tipo)
            encrypted = encrypt_payload(payload)
            try:
                client.table("painel_extracoes").update({"status": "substituido"}).eq("empresa_id", empresa_id).eq("tipo", tipo_registro).eq("status", "ativo").execute()
            except Exception:
                pass
            client.table("painel_extracoes").insert(
                {
                    "empresa_id": empresa_id,
                    "tipo": tipo_registro,
                    "status": "ativo",
                    "parametros": {"updated_by": user_id} if user_id else {},
                    "resultado": {"payload": encrypted},
                }
            ).execute()
        except CredentialsConfigError:
            raise
        except Exception as fallback_exc:
            raise CredentialsConfigError(
                "Falha ao salvar credenciais no Supabase: " + _safe_error(fallback_exc) + " | REST: " + _safe_error(exc)
            ) from fallback_exc