from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.automation_credentials import load_credentials

try:
    from automacoes.supabase_bases import _client, _resolve_empresa_id, supabase_configured
except Exception:
    _client = None
    _resolve_empresa_id = None

    def supabase_configured() -> bool:
        return False


def carregar_credencial_automacao(tipo: str, empresa_id: str = "", empresa_slug: str = "equipe-norte") -> dict[str, Any]:
    if not supabase_configured() or _client is None or _resolve_empresa_id is None:
        return {}
    client = _client()
    empresa = _resolve_empresa_id(client, empresa_id, empresa_slug)
    return load_credentials(client, empresa, tipo)
