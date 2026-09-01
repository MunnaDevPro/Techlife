from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("SEO Settings & Branding", {
            "fields": ("site_title", "meta_description", "favicon"),
        }),
        ("Analytics", {
            "fields": ("google_analytics_id",),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False