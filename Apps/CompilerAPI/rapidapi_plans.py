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
}


def _header(headers: Any, name: str) -> str | None:
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.upper())


def _rapidapi_subscription_from_request(request: Any) -> str:
    state = getattr(request, "state", None)

    plan = (
        getattr(state, "rapidapi_subscription", None)
        or _header(request.headers, "X-RapidAPI-Subscription")
        or _header(request.headers, "x-rapidapi-subscription")
        or "DIRECT"
    )

    return str(plan).upper()


def _rapidapi_user_from_request(request: Any) -> str | None:
    state = getattr(request, "state", None)

    user = (
        getattr(state, "rapidapi_user", None)
        or _header(request.headers, "X-RapidAPI-User")
        or _header(request.headers, "x-rapidapi-user")
    )

    return str(user) if user else None


def marketplace_account_from_request(
    request: Any,
    fallback_account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fallback_account = fallback_account or {}

    rapidapi_plan = _rapidapi_subscription_from_request(request)
    rapidapi_user = _rapidapi_user_from_request(request)

    if rapidapi_plan == "DIRECT":
        return {
            "rapidapi_plan": "DIRECT",
            "rapidapi_user": rapidapi_user,
            "product_plan": fallback_account.get("plan", "direct"),
            "used_this_month": fallback_account.get("used_this_month"),
            "monthly_limit": fallback_account.get("monthly_limit"),
            "artifact_export_enabled": True,
        }

    plan = RAPIDAPI_PLAN_MAP.get(
        rapidapi_plan,
        {
            "product_plan": "unknown",
            "monthly_limit": None,
            "artifact_export_enabled": False,
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


def artifact_export_allowed(request: Any) -> bool:
    return bool(marketplace_account_from_request(request)["artifact_export_enabled"])
