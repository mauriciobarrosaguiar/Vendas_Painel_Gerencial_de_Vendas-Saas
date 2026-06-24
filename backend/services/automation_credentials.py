from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet


CREDENTIAL_TYPES = {"bussola", "mercado_farma"}


class CredentialsConfigError(RuntimeError):
    pass


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
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


def load_credentials(client: Any, empresa_id: str, tipo: str) -> dict[str, Any]:
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
    except Exception as exc:
        raise CredentialsConfigError("Falha ao ler credenciais no Supabase: " + _safe_error(exc)) from exc


def save_credentials(
    client: Any,
    empresa_id: str,
    tipo: str,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
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
    except Exception as exc:
        raise CredentialsConfigError("Falha ao salvar credenciais no Supabase: " + _safe_error(exc)) from exc
