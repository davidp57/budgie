"""Shared SlowAPI rate-limiter instance.

Imported by :mod:`budgie.main` (to register the exception handler) and
by individual routers (to decorate endpoints).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from budgie.config import settings

#: Application-wide rate limiter keyed on the client IP address.
#: Set ``RATELIMIT_ENABLED=false`` in the environment to disable (e.g. tests).
limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)
