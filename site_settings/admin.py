from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("SEO Settings", {
            "fields": ("site_title", "meta_description"),
        }),
        ("Content Score control", {
            "fields": ("score_control",),
        }),
        ("Analytics", {
            "fields": ("google_analytics_id",),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False