"""
integrations/meta/utils.py
──────────────────────────
Low-level utility functions for the Meta Pixel / CAPI integration.

Responsibilities
  • SHA-256 hash PII fields (email, phone, name, etc.)
  • Generate deduplicated event_id values
  • Extract _fbp / _fbc cookies from the request
  • Resolve client IP (X-Forwarded-For aware)
  • Build the full user_data dict ready for the CAPI payload
"""
from __future__ import annotations

import hashlib
import time
import uuid
import re
import logging
from typing import Optional

logger = logging.getLogger("integrations.meta")


# ─────────────────────────────────────────────────────────────────────────────
# Hashing
# ─────────────────────────────────────────────────────────────────────────────

def sha256_hash(value: Optional[str]) -> Optional[str]:
    """
    Normalise and SHA-256 hash a PII string value.

    Meta requires all personal data to be:
      1. Lowercased and stripped of leading/trailing whitespace.
      2. Hashed with SHA-256 (hex digest).

    Returns None if the value is falsy so callers can use dict-comprehensions
    safely (e.g.  ``{k: v for k, v in data.items() if v}``).
    """
    if not value:
        return None
    normalised = value.strip().lower()
    if not normalised:
        return None
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def sha256_hash_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalise a phone number per Meta requirements before hashing:
      • Keep only digits and a leading '+'.
      • Lowercase (no-op for digits, but required by spec).
    """
    if not phone:
        return None
    # Strip everything except digits and leading +
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned:
        return None
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Event ID
# ─────────────────────────────────────────────────────────────────────────────

def generate_event_id() -> str:
    """
    Generate a universally unique event ID.

    Format:  evt_<unix_ms>_<uuid4_hex>
    Example: evt_1722178345123_a1b2c3d4e5f6...

    The timestamp prefix makes IDs sortable and the UUID suffix guarantees
    global uniqueness even under concurrent traffic.
    """
    ts_ms = int(time.time() * 1000)
    uid = uuid.uuid4().hex
    return f"evt_{ts_ms}_{uid}"


# ─────────────────────────────────────────────────────────────────────────────
# Request helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_client_ip(request) -> Optional[str]:
    """
    Return the real client IP, honouring X-Forwarded-For when present.
    The leftmost address in X-Forwarded-For is the original client.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def get_client_user_agent(request) -> Optional[str]:
    """Return the browser User-Agent string."""
    return request.META.get("HTTP_USER_AGENT") or None


def get_fbp(request) -> Optional[str]:
    """Return the _fbp cookie value (Facebook browser ID)."""
    return request.COOKIES.get("_fbp") or None


def get_fbc(request) -> Optional[str]:
    """
    Return the _fbc cookie value (Facebook click ID).

    If the cookie is absent, Meta allows constructing fbc from the
    fbclid query-string parameter:
      fbc = fb.1.<timestamp>.<fbclid>
    """
    fbc = request.COOKIES.get("_fbc")
    if fbc:
        return fbc
    fbclid = request.GET.get("fbclid")
    if fbclid:
        ts = int(time.time() * 1000)
        return f"fb.1.{ts}.{fbclid}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# User data builder
# ─────────────────────────────────────────────────────────────────────────────

def build_user_data(
    request,
    *,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    external_id: Optional[str] = None,
) -> dict:
    """
    Assemble a fully hashed user_data dict for the CAPI payload.

    All PII fields are SHA-256 hashed before they leave this function.
    Network-level fields (IP, UA, fbp, fbc) are NOT hashed — Meta expects
    them in plain text.

    Returns a dict with only the fields that have non-empty values.
    """
    # --- Try to enrich from the logged-in user ---
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        email = email or getattr(user, "email", None)
        first_name = first_name or getattr(user, "first_name", None)
        last_name = last_name or getattr(user, "last_name", None)
        # Use user's PK as external_id for strong cross-device matching
        if not external_id:
            external_id = str(user.pk)

    # --- Collect network signals (plain text, attached by middleware) ---
    meta_pixel_data: dict = getattr(request, "meta_pixel_data", {})
    client_ip = meta_pixel_data.get("client_ip_address") or get_client_ip(request)
    client_ua = meta_pixel_data.get("client_user_agent") or get_client_user_agent(request)
    fbp = meta_pixel_data.get("fbp") or get_fbp(request)
    fbc = meta_pixel_data.get("fbc") or get_fbc(request)

    user_data: dict = {}

    # Hashed PII
    if email:
        user_data["em"] = sha256_hash(email)
    if phone:
        user_data["ph"] = sha256_hash_phone(phone)
    if first_name:
        user_data["fn"] = sha256_hash(first_name)
    if last_name:
        user_data["ln"] = sha256_hash(last_name)
    if city:
        user_data["ct"] = sha256_hash(city)
    if state:
        user_data["st"] = sha256_hash(state)
    if zip_code:
        user_data["zp"] = sha256_hash(zip_code)
    if country:
        # Meta expects ISO 3166-1 alpha-2 country code, lowercase
        user_data["country"] = sha256_hash(country.lower())
    if external_id:
        user_data["external_id"] = sha256_hash(external_id)

    # Plain-text network signals
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_ua:
        user_data["client_user_agent"] = client_ua
    if fbp:
        user_data["fbp"] = fbp
    if fbc:
        user_data["fbc"] = fbc

    # Drop any None values (belt-and-suspenders)
    return {k: v for k, v in user_data.items() if v is not None}
