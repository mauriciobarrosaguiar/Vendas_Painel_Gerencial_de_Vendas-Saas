from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bussola_web import extrair_bussola_web_todos
from src.configuracoes import carregar_login_bussola
from src.datas import agora_brasilia

try:
    from automacoes.credenciais import carregar_credencial_automacao
except Exception:
    carregar_credencial_automacao = None


STATUS_PATH = ROOT / "data" / "bussola_status.json"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _log(msg: str) -> None:
    print(msg, flush=True)


def _login_json_env() -> dict:
    raw = _env("BUSSOLA_LOGIN_JSON")
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("BUSSOLA_LOGIN_JSON precisa ser um objeto JSON.")
    return data


def _login_config() -> dict:
    login: dict = {}
    if carregar_credencial_automacao is not None:
        try:
            login = carregar_credencial_automacao(
                "bussola",
                empresa_id=_env("SUPABASE_EMPRESA_ID"),
                empresa_slug=_env("SUPABASE_EMPRESA_SLUG", "equipe-norte"),
            )
        except Exception as exc:
            _log(f"Aviso: nao consegui carregar credenciais Bussola do Supabase: {exc}")
    if not login:
        login = _login_json_env()
    login = login or carregar_login_bussola()
    if not isinstance(login, dict):
        login = {}
    login.setdefault("gd", {})
    login.setdefault("consultores", {})

    gd_usuario = _env("BUSSOLA_GD_USUARIO") or _env("BUSSOLA_USUARIO")
    gd_senha = _env("BUSSOLA_GD_SENHA") or _env("BUSSOLA_SENHA")
    if gd_usuario or gd_senha:
        gd = login.get("gd", {}) if isinstance(login.get("gd"), dict) else {}
        gd.update(
            {
                "usuario": gd_usuario or str(gd.get("usuario", "")),
                "senha": gd_senha or str(gd.get("senha", "")),
                "usar_gd": True,
            }
        )
        login["gd"] = gd
    return login


def _credenciais_bussola(login: dict) -> tuple[list[dict[str, str]], list[str]]:
    gd = login.get("gd", {}) if isinstance(login.get("gd"), dict) else {}
    gd_usuario = str(gd.get("usuario", "") or "").strip()
    gd_senha = str(gd.get("senha", "") or "").strip()
    usar_gd = bool(gd.get("usar_gd", True))
    nome_gd = _env("BUSSOLA_GD_NOME", "Gerente Distrital")
    if usar_gd and gd_usuario and gd_senha:
        return [{"consultor": f"GD - {nome_gd}", "usuario": gd_usuario, "senha": gd_senha}], []

    solicitados: list[dict[str, str]] = []
    consultores = login.get("consultores", {}) if isinstance(login.get("consultores"), dict) else {}
    for consultor, item in consultores.items():
        dados = item if isinstance(item, dict) else {}
        if not bool(dados.get("extrair", True)):
            continue
        solicitados.append(
            {
                "consultor": str(consultor),
                "usuario": str(dados.get("usuario", "") or "").strip(),
                "senha": str(dados.get("senha", "") or "").strip(),
            }
        )
    incompletos = [item["consultor"] for item in solicitados if not item["usuario"] or not item["senha"]]
    credenciais = [item for item in solicitados if item["usuario"] and item["senha"]]
    return credenciais, incompletos


def _salvar_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai Bussola Web usando a regra do painel Streamlit.")
    parser.add_argument("--headless", action="store_true", help="Executa navegador oculto.")
    args = parser.parse_args()

    status = {
        "status": "erro",
        "total_credenciais": 0,
        "incompletos": [],
        "arquivo": "",
        "erro": "",
        "traceback": "",
        "iniciado_em": agora_brasilia().isoformat(),
        "finalizado_em": "",
    }
    try:
        login = _login_config()
        credenciais, incompletos = _credenciais_bussola(login)
        status["total_credenciais"] = len(credenciais)
        status["incompletos"] = incompletos
        if incompletos:
            _log("Consultores ignorados por login/senha incompletos: " + ", ".join(incompletos))
        if not credenciais:
            raise RuntimeError("Nenhuma credencial Bussola configurada para extracao.")

        _log(f"Iniciando extracao Bussola com {len(credenciais)} credencial(is).")
        destino = extrair_bussola_web_todos(credenciais, headless=args.headless, log_fn=_log)
        status["status"] = "sucesso"
        status["arquivo"] = str(destino.relative_to(ROOT) if destino.is_relative_to(ROOT) else destino)
        _log(f"Arquivo Bussola consolidado: {destino}")
        status["finalizado_em"] = agora_brasilia().isoformat()
        _salvar_status(status)
        return 0
    except Exception as exc:
        status["erro"] = str(exc)
        status["traceback"] = traceback.format_exc(limit=8)
        status["finalizado_em"] = agora_brasilia().isoformat()
        _log(f"Erro na extracao Bussola: {exc}")
        _log(status["traceback"])
        _salvar_status(status)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
