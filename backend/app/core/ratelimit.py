"""Per-IP rate limiting using slowapi.

Mounted in main.py. Two key surfaces are protected:
  * /auth/login — bruteforce defence
  * /ai/* — cost defence; AI calls are expensive
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])

AUTH_LIMIT = "10/minute"
AI_LIMIT = "30/minute"
