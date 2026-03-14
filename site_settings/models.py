from django.db import models

class SiteSettings(models.Model):
    # Analytics
    google_analytics_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Google Analytics Measurement ID (e.g., G-XXXXXXXXXX)"
    )
    
    # SEO
    site_title = models.CharField(
        max_length=200,
        default="TechLife || Know The Current Situation",
        help_text="The main title of the website."
    )
    meta_description = models.TextField(
        blank=True,
        null=True,
        help_text="The meta description for the website (recommended length is under 160 characters)."
    )
    
    score_control = models.CharField(max_length=3, null=True, blank=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Ensure only one instance of settings exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj