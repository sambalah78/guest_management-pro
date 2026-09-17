"""Authentication health API for EventLah."""

from fastapi import FastAPI

api = FastAPI(title="EventLah Auth API")


@api.get("/api/auth/health")
def auth_health():
    return {"ok": True}