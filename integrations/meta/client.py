"""
integrations/meta/client.py
────────────────────────────
Low-level HTTP client for the Meta Conversions API (CAPI).

Uses only Python standard-library modules (urllib) — no extra dependencies.

Features
  • 10-second request timeout
  • Up to 3 retries with exponential back-off (1 s, 2 s, 4 s)
  • Structured success / failure logging
  • Access token NEVER appears in logs
  • Graceful degradation — any exception is caught and logged
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger("integrations.meta")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_REQUEST_TIMEOUT = 10        # seconds per attempt
_MAX_RETRIES = 3             # total attempts (1 initial + 2 retries)
_RETRY_BASE_DELAY = 1.0      # seconds (doubles each retry: 1, 2, 4)
_GRAPH_API_BASE = "https://graph.facebook.com"


class MetaAPIClient:
    """
    Thin, dependency-free wrapper around the Meta Conversions API.

    Instantiate once (e.g. inside MetaPixelService) and reuse.
    The client is automatically a no-op when settings are missing.
    """

    def __init__(self) -> None:
        self._pixel_id: str = getattr(settings, "META_PIXEL_ID", "")
        self._access_token: str = getattr(settings, "META_ACCESS_TOKEN", "")
        self._api_version: str = getattr(settings, "META_API_VERSION", "v23.0")
        self._test_event_code: str = getattr(settings, "META_TEST_EVENT_CODE", "")
        self._enabled: bool = bool(self._pixel_id and self._access_token)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def send_event(self, event_payload: dict) -> Optional[dict]:
        """
        Send a single event to the Meta Conversions API.

        ``event_payload`` must be a dict matching the Meta CAPI event schema:
        https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/

        Returns the parsed JSON response body on success, or None on failure.
        The access token is injected server-side and never logged.
        """
        if not self._enabled:
            logger.debug(
                "Meta CAPI disabled (no PIXEL_ID or ACCESS_TOKEN). Skipping event: %s",
                event_payload.get("event_name", "unknown"),
            )
            return None

        url = (
            f"{_GRAPH_API_BASE}/{self._api_version}"
            f"/{self._pixel_id}/events"
        )

        payload: dict[str, Any] = {
            "data": [event_payload],
            "access_token": self._access_token,  # injected here, not logged
        }
        if self._test_event_code:
            payload["test_event_code"] = self._test_event_code

        return self._post_with_retry(url, payload, event_payload)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _post_with_retry(
        self,
        url: str,
        payload: dict,
        event_payload: dict,
    ) -> Optional[dict]:
        """POST with exponential back-off retries."""
        event_name = event_payload.get("event_name", "unknown")
        event_id = event_payload.get("event_id", "—")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._http_post(url, payload)
                logger.info(
                    "Meta Event Sent | event=%s | event_id=%s | status=success | response=%s",
                    event_name,
                    event_id,
                    response,
                )
                return response

            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                logger.warning(
                    "Meta Event Failed | event=%s | event_id=%s | attempt=%d/%d "
                    "| status=%d | response=%s",
                    event_name,
                    event_id,
                    attempt,
                    _MAX_RETRIES,
                    exc.code,
                    body,
                )
                # 4xx errors are client errors — no point retrying
                if 400 <= exc.code < 500:
                    return None

            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                logger.warning(
                    "Meta Event Failed | event=%s | event_id=%s | attempt=%d/%d "
                    "| status=network_error | error=%s",
                    event_name,
                    event_id,
                    attempt,
                    _MAX_RETRIES,
                    type(exc).__name__,
                )

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Meta Event Failed | event=%s | event_id=%s | status=unexpected_error "
                    "| error=%s",
                    event_name,
                    event_id,
                    repr(exc),
                )
                return None  # Don't retry on unexpected errors

            # Exponential back-off before next attempt
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)

        # All retries exhausted
        logger.error(
            "Meta Event Failed | event=%s | event_id=%s | status=max_retries_exceeded",
            event_name,
            event_id,
        )
        return None

    @staticmethod
    def _http_post(url: str, payload: dict) -> dict:
        """
        Perform a single HTTPS POST and return the parsed JSON response.

        The raw ``payload`` dict is JSON-encoded before sending.
        Uses urllib.request — no third-party dependency required.
        """
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
