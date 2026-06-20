from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from acbp_compiler import ACBPCompilerApiService, ACBPCompilerProductService


API_HOME = Path(r"D:\ACBP\Apps\CompilerAPI")
PROJECT_HOME = API_HOME / "product_data"
KEYS_PATH = API_HOME / "api_keys.json"
USAGE_PATH = API_HOME / "usage.json"

API_HOME.mkdir(parents=True, exist_ok=True)
PROJECT_HOME.mkdir(parents=True, exist_ok=True)

DEFAULT_KEYS = {
    "acbp_free_demo": {
        "plan": "free",
        "monthly_limit": 25,
        "max_truth_space": 10_000,
    },
    "acbp_starter_dev": {
        "plan": "starter",
        "monthly_limit": 500,
        "max_truth_space": 100_000,
    },
    "acbp_builder_dev": {
        "plan": "builder",
        "monthly_limit": 3_000,
        "max_truth_space": 1_000_000,
    },
}


def ensure_default_keys() -> None:
    if not KEYS_PATH.exists():
        KEYS_PATH.write_text(
            json.dumps(DEFAULT_KEYS, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def load_keys() -> dict[str, Any]:
    ensure_default_keys()
    return json.loads(KEYS_PATH.read_text(encoding="utf-8"))


def load_usage() -> dict[str, Any]:
    if not USAGE_PATH.exists():
        return {}

    try:
        return json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_usage(usage: dict[str, Any]) -> None:
    USAGE_PATH.write_text(
        json.dumps(usage, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def boolify(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def require_api_key(
    x_acbp_api_key: str | None = Header(default=None, alias="X-ACBP-API-Key"),
) -> dict[str, Any]:
    keys = load_keys()

    if not x_acbp_api_key or x_acbp_api_key not in keys:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Use X-ACBP-API-Key.",
        )

    cfg = dict(keys[x_acbp_api_key])
    limit = int(cfg.get("monthly_limit", 0))

    usage = load_usage()
    mk = month_key()

    key_usage = usage.setdefault(x_acbp_api_key, {})
    current = int(key_usage.get(mk, 0))

    if limit and current >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exceeded for plan {cfg.get('plan')}.",
        )

    key_usage[mk] = current + 1
    save_usage(usage)

    cfg["api_key"] = x_acbp_api_key
    cfg["used_this_month"] = key_usage[mk]
    cfg["month"] = mk

    return cfg


def enforce_truth_space_limit(result: dict[str, Any], account: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    max_allowed = int(account.get("max_truth_space", 10_000))

    truth_space = (
        summary.get("truth_space_size")
        or summary.get("estimated_boolean_state_space")
        or summary.get("estimate", {}).get("truth_space_size")
        or 0
    )

    try:
        truth_space = int(truth_space)
    except Exception:
        truth_space = 0

    if truth_space > max_allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Truth space {truth_space:,} exceeds plan limit "
                f"{max_allowed:,}. Upgrade plan or reduce dimensions."
            ),
        )


app = FastAPI(
    title="ACBP Truth Compiler API",
    version="0.1.0",
    description=(
        "Paid plugin API for compiling categories, flags, dashboard states, "
        "and workflow logic into declared-truth artifacts."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

product_service = ACBPCompilerProductService(product_home=PROJECT_HOME)
compiler_api = ACBPCompilerApiService(product_service=product_service)


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "ACBP Truth Compiler API",
        "version": "0.1.0",
        "market_position": "declared-truth compiler for dashboards, categories, and workflow states",
    }


@app.get("/v1/pricing")
def pricing() -> dict[str, Any]:
    return {
        "free": {
            "price": "$0",
            "monthly_compiles": 25,
            "max_truth_space": 10_000,
        },
        "starter": {
            "price": "$9/month",
            "monthly_compiles": 500,
            "max_truth_space": 100_000,
        },
        "builder": {
            "price": "$29/month",
            "monthly_compiles": 3_000,
            "max_truth_space": 1_000_000,
        },
        "pro": {
            "price": "$79/month",
            "monthly_compiles": 15_000,
            "max_truth_space": 10_000_000,
            "note": "Configure this key when ready.",
        },
    }


@app.get("/v1/examples")
def examples() -> dict[str, Any]:
    return {
        "truth_space_compile": {
            "endpoint": "POST /v1/truth-space/compile",
            "headers": {"X-ACBP-API-Key": "acbp_free_demo"},
            "body": {
                "name": "object_color",
                "dimensions": [
                    {"name": "TargetClass", "values": ["Apple", "Banana", "Mango"]},
                    {"name": "Color", "values": ["Red", "Yellow", "Green"]},
                ],
                "declared_truths": [
                    {"TargetClass": "Apple", "Color": "Red"},
                    {"TargetClass": "Apple", "Color": "Green"},
                ],
            },
        },
        "compact_features": {
            "endpoint": "POST /v1/features/compact",
            "headers": {"X-ACBP-API-Key": "acbp_free_demo"},
            "body": {
                "target_cardinality": 3,
                "n_rows": 240,
                "columns": [
                    {"name": "Case_ID", "type": "id", "unique": 240},
                    {"name": "Delay_Bucket", "type": "category", "unique": 5},
                    {"name": "ASA_Class", "type": "category", "unique": 5},
                ],
                "max_truth_space": 20000,
            },
        },
        "dashboard_compare": {
            "endpoint": "POST /v1/dashboard/compare",
            "headers": {"X-ACBP-API-Key": "acbp_free_demo"},
            "body": {
                "live_sql_result": [{"unit": "A", "live_census": 10}],
                "cbp_result": [{"unit": "A", "live_census": 10}],
                "key_cols": ["unit"],
            },
        },
    }


@app.post("/v1/truth-space/compile")
def truth_space_compile(
    payload: dict[str, Any],
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    save_artifact = boolify(payload.get("save_artifact", False))

    result = compiler_api.compile_truth_space(
        payload=payload,
        save_artifact=save_artifact,
    )

    enforce_truth_space_limit(result, account)

    result["account"] = {
        "plan": account.get("plan"),
        "used_this_month": account.get("used_this_month"),
        "monthly_limit": account.get("monthly_limit"),
    }

    return result


@app.post("/v1/features/compact")
def features_compact(
    payload: dict[str, Any],
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    save_artifact = boolify(payload.get("save_artifact", False))

    payload = dict(payload)
    payload["max_truth_space"] = min(
        int(payload.get("max_truth_space", account.get("max_truth_space", 10_000))),
        int(account.get("max_truth_space", 10_000)),
    )

    result = compiler_api.compact_features(
        payload=payload,
        save_artifact=save_artifact,
    )

    enforce_truth_space_limit(result, account)

    result["account"] = {
        "plan": account.get("plan"),
        "used_this_month": account.get("used_this_month"),
        "monthly_limit": account.get("monthly_limit"),
    }

    return result


@app.post("/v1/dashboard/compare")
def dashboard_compare(
    payload: dict[str, Any],
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    save_artifact = boolify(payload.get("save_artifact", False))

    result = compiler_api.compare_dashboard(
        payload=payload,
        save_artifact=save_artifact,
    )

    result["account"] = {
        "plan": account.get("plan"),
        "used_this_month": account.get("used_this_month"),
        "monthly_limit": account.get("monthly_limit"),
    }

    return result


@app.get("/v1/clinical-dashboard/spec")
def clinical_dashboard_spec(
    save_artifact: bool = False,
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    result = compiler_api.clinical_dashboard_spec(save_artifact=save_artifact)

    enforce_truth_space_limit(result, account)

    result["account"] = {
        "plan": account.get("plan"),
        "used_this_month": account.get("used_this_month"),
        "monthly_limit": account.get("monthly_limit"),
    }

    return result


@app.get("/v1/projects")
def projects(
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    return {
        "projects": product_service.list_projects(),
        "account": {
            "plan": account.get("plan"),
            "used_this_month": account.get("used_this_month"),
            "monthly_limit": account.get("monthly_limit"),
        },
    }


@app.get("/v1/projects/{project_id}")
def project_detail(
    project_id: str,
    account: dict[str, Any] = Depends(require_api_key),
) -> dict[str, Any]:
    try:
        return product_service.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc

# --- ACBP cloud marketplace security ---
try:
    from Apps.CompilerAPI.security import install_marketplace_security
except ModuleNotFoundError:
    from security import install_marketplace_security

install_marketplace_security(app)
# --- end ACBP cloud marketplace security ---

# --- ACBP public export route ---
try:
    from fastapi.responses import FileResponse
except Exception:
    FileResponse = None

@app.get("/v1/projects/{project_id}/export")
def export_project_v1(project_id: str):
    if FileResponse is None:
        raise RuntimeError("FileResponse is not available.")

    zip_path = product_service.export_project_zip(project_id)
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"{project_id}.zip",
    )
# --- end ACBP public export route ---

# --- ACBP public and legacy export routes ---
from fastapi.responses import FileResponse

def _export_project_zip_response(project_id: str):
    zip_path = product_service.export_project_zip(project_id)
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"{project_id}.zip",
    )

@app.get("/v1/projects/{project_id}/export")
def export_project_v1(project_id: str):
    return _export_project_zip_response(project_id)

@app.get("/api/projects/{project_id}/export")
def export_project_legacy_api(project_id: str):
    return _export_project_zip_response(project_id)
# --- end ACBP public and legacy export routes ---
