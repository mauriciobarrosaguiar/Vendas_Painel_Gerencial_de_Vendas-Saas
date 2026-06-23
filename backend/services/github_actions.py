from __future__ import annotations

import os
from typing import Any

import requests


class GitHubActionsConfigError(RuntimeError):
    pass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _config() -> dict[str, str]:
    repo = _env("GITHUB_REPO", "mauriciobarrosaguiar/Vendas_Painel_Gerencial_de_Vendas-Saas")
    branch = _env("GITHUB_BRANCH", "main")
    token = _env("GITHUB_TOKEN")
    missing = []
    if not repo:
        missing.append("GITHUB_REPO")
    if not token:
        missing.append("GITHUB_TOKEN")
    if missing:
        raise GitHubActionsConfigError("Variaveis ausentes: " + ", ".join(missing))
    return {"repo": repo, "branch": branch, "token": token}


def is_configured() -> bool:
    return bool(_env("GITHUB_TOKEN") and _env("GITHUB_REPO", "mauriciobarrosaguiar/Vendas_Painel_Gerencial_de_Vendas-Saas"))


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def dispatch_workflow(workflow: str, inputs: dict[str, str], *, branch: str | None = None) -> dict[str, Any]:
    cfg = _config()
    ref = branch or cfg["branch"]
    url = f"https://api.github.com/repos/{cfg['repo']}/actions/workflows/{workflow}/dispatches"
    response = requests.post(
        url,
        headers=_headers(cfg["token"]),
        json={"ref": ref, "inputs": inputs},
        timeout=30,
    )
    if response.status_code != 204:
        detail = response.text[:500] if response.text else response.reason
        raise RuntimeError(f"Falha ao disparar workflow {workflow}: HTTP {response.status_code} - {detail}")
    return {"workflow": workflow, "repo": cfg["repo"], "branch": ref, "inputs": inputs}


def list_workflow_runs(workflow: str, *, limit: int = 5) -> list[dict[str, Any]]:
    cfg = _config()
    url = f"https://api.github.com/repos/{cfg['repo']}/actions/workflows/{workflow}/runs"
    response = requests.get(
        url,
        headers=_headers(cfg["token"]),
        params={"branch": cfg["branch"], "per_page": max(1, min(limit, 20))},
        timeout=30,
    )
    if response.status_code != 200:
        detail = response.text[:500] if response.text else response.reason
        raise RuntimeError(f"Falha ao listar execucoes de {workflow}: HTTP {response.status_code} - {detail}")
    data = response.json()
    runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
    return runs if isinstance(runs, list) else []
