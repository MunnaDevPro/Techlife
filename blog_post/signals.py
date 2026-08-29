from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import HomepageConfig, BlogPost
from notification.models import Notification

@receiver(post_save, sender=HomepageConfig)
@receiver(post_delete, sender=HomepageConfig)
def clear_homepage_cache(sender, instance, **kwargs):
    cache.delete(f"homepage_config_{instance.section_key}")

@receiver(pre_save, sender=BlogPost)
def track_blogpost_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = BlogPost.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except BlogPost.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=BlogPost)
def notify_author_on_status_change(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    if not created and old_status and old_status != instance.status:
        # Status has changed!
        if instance.status == "published":
            title = "Post Published!"
            message = f"Congratulations! Your post '{instance.title}' has been published."
            target_url = f"/details/{instance.slug}/" if instance.slug else "#"
            
            Notification.objects.create(
                user=instance.author,
                title=title,
                message=message,
                target_url=target_url
            )
            
        elif instance.status == "rejected":
            title = "Post Rejected"
            message = f"Unfortunately, your post '{instance.title}' was rejected."
            target_url = f"/blogs/{instance.slug}/edit/" if instance.slug else "#"
            
            Notification.objects.create(
                user=instance.author,
                title=title,
                message=message,
                target_url=target_url
            )
