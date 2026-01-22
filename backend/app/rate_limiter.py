"""Rate limiter configuration for auth endpoints."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - shared across modules
limiter = Limiter(key_func=get_remote_address)
