from .models import SiteSettings

def site_settings(request):
    settings = SiteSettings.get_settings()
    return {
        'site_settings': settings,
        'GOOGLE_ANALYTICS_ID': settings.google_analytics_id,
        'GTM_ID': settings.gtm_id,
        'META_PIXEL_ID': settings.meta_pixel_id,
        'SITE_TITLE': settings.site_title,
        'META_DESCRIPTION': settings.meta_description,
    }
