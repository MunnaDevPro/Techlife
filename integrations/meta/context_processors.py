"""
integrations/meta/context_processors.py
─────────────────────────────────────────
Injects META_PIXEL_ID into every template context.

SECURITY NOTE:
  Only META_PIXEL_ID is exposed here — it is safe to render in HTML.
  META_ACCESS_TOKEN is NEVER added to any template context.
"""
from django.conf import settings


def meta_pixel(request) -> dict:
    """
    Add META_PIXEL_ID to the template context.

    When META_PIXEL_ID is empty, the pixel snippet template tag
    renders nothing (conditional on the value being truthy).
    """
    return {
        "META_PIXEL_ID": getattr(settings, "META_PIXEL_ID", ""),
    }
