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

        return await call_next(request)
