
from django import template
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince

register = template.Library()

@register.filter
def humanize_number(value):

    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    if value >= 1_000_000:
     
        return f"{value / 1_000_000:.1f}M"
    elif value >= 10_000:
       
        return f"{value / 1000:.0f}k"
    elif value >= 1_000:
      
        return f"{value / 1000:.1f}k"
    else:
      
        return value
    
    


@register.filter
def first_timesince(value):

    if not value:
        return ""
        
    ts = timesince(value)

    first_part = ts.split(',')[0].strip()
    
    return first_part


@register.filter
def render_stars(rating):
    """
    Renders 5 stars HTML based on numeric rating (1-5).
    """
    try:
        val = float(rating or 0)
    except (ValueError, TypeError):
        val = 0.0

    html = []
    for i in range(1, 6):
        if val >= i:
            html.append('<i class="fas fa-star text-[#ffb800]"></i>')
        elif val >= i - 0.5:
            html.append('<i class="fas fa-star-half-alt text-[#ffb800]"></i>')
        else:
            html.append('<i class="far fa-star text-gray-300"></i>')
    return mark_safe("".join(html))