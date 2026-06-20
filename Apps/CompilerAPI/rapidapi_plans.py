from __future__ import annotations

from typing import Any


RAPIDAPI_PLAN_MAP: dict[str, dict[str, Any]] = {
    "BASIC": {
        "product_plan": "free",
        "monthly_limit": 25,
        "artifact_export_enabled": False,
    },
    "PRO": {
        "product_plan": "starter",
        "monthly_limit": 500,
        "artifact_export_enabled": True,
    },
    "ULTRA": {
        "product_plan": "builder",
        "monthly_limit": 3000,
        "artifact_export_enabled": True,
    },
    "MEGA": {
        "product_plan": "pro",
        "monthly_limit": 15000,
        "artifact_export_enabled": True,
    },
    "CUSTOM": {
        "product_plan": "custom",
        "monthly_limit": None,
        "artifact_export_enabled": True,
    },
}


def marketplace_account_from_headers(headers) -> dict[str, Any]:
    rapidapi_plan = (
        headers.get("x-rapidapi-subscription")
        or headers.get("X-RapidAPI-Subscription")
        or "DIRECT"
    ).upper()

    rapidapi_user = (
        headers.get("x-rapidapi-user")
        or headers.get("X-RapidAPI-User")
        or None
    )

    plan = RAPIDAPI_PLAN_MAP.get(
        rapidapi_plan,
        {
            "product_plan": "direct",
            "monthly_limit": None,
            "artifact_export_enabled": True,
        },
    )

    return {
        "rapidapi_plan": rapidapi_plan,
        "rapidapi_user": rapidapi_user,
        "product_plan": plan["product_plan"],
        "used_this_month": None,
        "monthly_limit": plan["monthly_limit"],
        "artifact_export_enabled": plan["artifact_export_enabled"],
    }


def artifact_export_allowed(headers) -> bool:
    return bool(marketplace_account_from_headers(headers)["artifact_export_enabled"])
