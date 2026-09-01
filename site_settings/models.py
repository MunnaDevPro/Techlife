from django.db import models

class SiteSettings(models.Model):
    # Analytics
    google_analytics_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Google Analytics Measurement ID (e.g., G-XXXXXXXXXX)"
    )
    gtm_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Google Tag Manager ID (e.g., GTM-XXXXXXX)"
    )
    meta_pixel_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Meta Pixel ID (e.g., 1234567890)"
    )
    
    # SEO
    site_title = models.CharField(
        max_length=200,
        default="TechLife || Know The Current Situation",
        help_text="Website এর Main Title"
    )
    meta_description = models.TextField(
        blank=True,
        null=True,
        help_text="Website এর Meta Description (160 character এর মধ্যে রাখুন)"
    )
    favicon = models.ImageField(
        upload_to="site/favicon/",
        blank=True,
        null=True,
        help_text="Website এর Favicon আপলোড করুন (Standard size: 32x32 or 16x16)"
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj