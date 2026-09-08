from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("Branding & Logo", {
            "fields": ("logo", "logo_dark", "favicon"),
        }),
        ("SEO Settings", {
            "fields": ("site_title", "meta_description"),
        }),
        ("Analytics", {
            "fields": ("google_analytics_id",),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False