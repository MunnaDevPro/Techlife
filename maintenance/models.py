from django.db import models
from django.utils import timezone


class MaintenanceSettings(models.Model):

    site_under_maintenance = models.BooleanField(
        default=False,
        verbose_name="Entire Website",
        help_text="Activates maintenance mode across all pages.",
    )
    forum_under_maintenance = models.BooleanField(
        default=False,
        verbose_name="Forum Section",
        help_text="Activates maintenance mode on forum pages only.",
    )
    
    custom_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Custom Message",
        help_text="Optional message to display on the maintenance screen.",
    )

    # ── Countdown end time ──────────────────────────────────────────
    maintenance_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Maintenance Until",
        help_text=(
            "Set the date and time when maintenance will end. "
            "A live countdown will display on the modal. Leave blank to hide the timer."
        ),
    )

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maintenance Settings"
        verbose_name_plural = "Maintenance Settings"

    def __str__(self):
        parts = []
        if self.site_under_maintenance:
            parts.append("Site")
        if self.forum_under_maintenance:
            parts.append("Forum")
        return "Active — " + ", ".join(parts) if parts else "All systems operational"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj