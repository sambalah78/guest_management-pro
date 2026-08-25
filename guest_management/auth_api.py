"""Google OAuth callback API mounted into Reflex via FastAPI."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
from guest_management.core.config import settings
from guest_management.services.auth_service import AuthService

api = FastAPI(title="EventLah Auth API")

@api.get("/api/auth/google/callback")
def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error: return RedirectResponse(f"{settings.app_url}/login?error=google_denied")
    expected = request.cookies.get("eventlah_oauth_state")
    if not code or not state or not expected or state != expected:
        return PlainTextResponse("Invalid OAuth state", status_code=400)
    try:
        result = AuthService().exchange_code(code)
    except Exception:
        return RedirectResponse(f"{settings.app_url}/login?error=google_auth_failed")
    response = RedirectResponse(f"{settings.app_url}/events")
    response.set_cookie("eventlah_session", result["session"], max_age=settings.session_ttl_seconds, path="/",
                        secure=settings.is_production, httponly=False, samesite="lax")
    response.delete_cookie("eventlah_oauth_state", path="/")
    return response

@api.get("/api/auth/health")
def auth_health(): return {"ok": True, "google_configured": bool(settings.google_client_id and settings.google_client_secret)}
