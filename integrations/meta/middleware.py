"""
integrations/meta/middleware.py
────────────────────────────────
MetaPixelMiddleware — automatically captures per-request signals
needed by the Meta Conversions API.

After this middleware runs, every request object will have:

    request.meta_pixel_data = {
        "client_ip_address": str | None,
        "client_user_agent": str | None,
        "fbp": str | None,   # _fbp cookie
        "fbc": str | None,   # _fbc cookie or constructed from fbclid
    }

This keeps views clean — they just read from ``request.meta_pixel_data``
instead of manually parsing cookies and headers.

The middleware is a no-op when META_PIXEL_ID is not configured.
"""
from __future__ import annotations

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .utils import get_client_ip, get_client_user_agent, get_fbp, get_fbc


class MetaPixelMiddleware(MiddlewareMixin):
    """
    Lightweight request-enrichment middleware for the Meta integration.

    Attaches ``request.meta_pixel_data`` on every incoming request.
    If META_PIXEL_ID is empty, sets the dict to empty (safe no-op).
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self._enabled = bool(getattr(settings, "META_PIXEL_ID", ""))

    def process_request(self, request) -> None:
        """Attach meta_pixel_data to the request before the view executes."""
        if not self._enabled:
            request.meta_pixel_data = {}
            return

        request.meta_pixel_data = {
            "client_ip_address": get_client_ip(request),
            "client_user_agent": get_client_user_agent(request),
            "fbp": get_fbp(request),
            "fbc": get_fbc(request),
        }
