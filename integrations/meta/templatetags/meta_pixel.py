"""
integrations/meta/templatetags/meta_pixel.py
─────────────────────────────────────────────
Provides the ``{% meta_pixel %}`` inclusion template tag.

Usage in any template:

    {% load meta_pixel %}
    {% meta_pixel %}

The tag renders ``integrations/meta_pixel.html`` which contains:
  • The fbq() pixel initialisation script
  • The <noscript> fallback image
  • A <script> tag that loads meta.js (the JS helper)

The entire block renders as an empty string when META_PIXEL_ID is absent,
so no tracking code ever appears in the HTML without configuration.
"""
from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag("integrations/meta_pixel.html", takes_context=True)
def meta_pixel(context):
    """
    Render the Meta Pixel initialisation snippet.

    Passes META_PIXEL_ID from settings (not from template context, to be safe).
    The access token is never passed to templates.
    """
    pixel_id = getattr(settings, "META_PIXEL_ID", "")
    return {
        "META_PIXEL_ID": pixel_id,
        "meta_pixel_enabled": bool(pixel_id),
        # Forward the request so the template can use {% url %} etc. if needed
        "request": context.get("request"),
    }
