from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import HomepageConfig


@receiver(post_save, sender=HomepageConfig)
@receiver(post_delete, sender=HomepageConfig)
def clear_homepage_cache(sender, instance, **kwargs):
    cache.delete(f'homepage_config_{instance.section_key}')
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import HomepageConfig


@receiver(post_save, sender=HomepageConfig)
@receiver(post_delete, sender=HomepageConfig)
def clear_homepage_cache(sender, instance, **kwargs):
    cache.delete(f"homepage_config_{instance.section_key}")
