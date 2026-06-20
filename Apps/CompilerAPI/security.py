import hmac
import os
from starlette.responses import JSONResponse


PUBLIC_PATHS = {
    "/",
    "/v1/health",
    "/v1/pricing",
    "/v1/examples",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _inject_internal_api_key(request) -> None:
    """
    RapidAPI handles subscriber auth, quota, and billing.
    After RapidAPI proxy-secret validation succeeds, inject an internal
    ACBP API key so the existing local API-key dependency can continue working.
    """

    internal_key = os.getenv("ACBP_RAPIDAPI_INTERNAL_KEY", "acbp_builder_dev").strip()

    headers = list(request.scope.get("headers", []))

    # Remove any external attempt to send X-ACBP-API-Key directly.
    headers = [
        (k, v)
        for (k, v) in headers
        if k.lower() != b"x-acbp-api-key"
    ]

    headers.append((b"x-acbp-api-key", internal_key.encode("utf-8")))
    request.scope["headers"] = headers

    # Starlette may cache request.headers before we inject; reset cache.
    if hasattr(request, "_headers"):
        delattr(request, "_headers")


def install_marketplace_security(app):
    """
    Production gate for marketplace deployment.

    Local/dev mode:
      ACBP_REQUIRE_RAPIDAPI is false or unset.
      Existing local X-ACBP-API-Key behavior remains available.

    Production/RapidAPI mode:
      ACBP_REQUIRE_RAPIDAPI=true
      RAPIDAPI_PROXY_SECRET must be set.
      Requests must include matching X-RapidAPI-Proxy-Secret.
      Then the middleware injects an internal X-ACBP-API-Key.
    """

    @app.middleware("http")
    async def acbp_marketplace_security(request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        require_rapidapi = _truthy(os.getenv("ACBP_REQUIRE_RAPIDAPI"))

        if not require_rapidapi:
            return await call_next(request)

        expected_secret = os.getenv("RAPIDAPI_PROXY_SECRET", "").strip()

        if not expected_secret:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_configuration_error",
                    "message": "RAPIDAPI_PROXY_SECRET is not configured.",
                },
            )

        received_secret = request.headers.get("X-RapidAPI-Proxy-Secret", "").strip()

        if not hmac.compare_digest(received_secret, expected_secret):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "forbidden",
                    "message": "This production API only accepts authorized marketplace traffic.",
                },
            )

        request.state.rapidapi_user = request.headers.get("X-RapidAPI-User", "")
        request.state.rapidapi_subscription = request.headers.get("X-RapidAPI-Subscription", "")

        _inject_internal_api_key(request)

        return await call_next(request)
