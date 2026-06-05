"""Rate limiting using slowapi.

Mounted in main.py. Two key surfaces are protected:
  * /auth/login — bruteforce defence, per IP
  * /ai/*       — cost defence (AI calls cost real money), per IP for the
                  triage / draft endpoints (used by lots of staff at once);
                  per USER for /ai/chat where a single signed-in user with
                  a script could rack up tokens regardless of egress IP.

`get_remote_address` honours X-Forwarded-For when running behind a proxy
(slowapi reads request.client.host which uvicorn populates from proxy
headers when --proxy-headers is set).
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_key(request: Request) -> str:
    """Best-effort per-user key. Falls back to IP if no auth header.

    We don't decode the JWT here (would need the DB / settings); the raw
    token is a stable enough identifier for rate-limit bucketing. A user
    signed in twice on two devices shares the budget — that's intended.
    """
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return f"user:{auth[7:]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_remote_address, default_limits=[])

AUTH_LIMIT = "10/minute"
AI_LIMIT = "30/minute"        # per IP (triage + draft endpoints)
ASSISTANT_LIMIT = "20/minute"  # per user (chat — paired with _user_key)
