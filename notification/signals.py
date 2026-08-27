from django.db.models.signals import post_save
from django.dispatch import receiver
from blog_post.models import BlogPost
from .models import Notification
from django.urls import reverse

@receiver(post_save, sender=BlogPost)
def create_post_notification(sender, instance, created, **kwargs):
    # Whenever a new blog post is created and its status is pending, notify admins
    if created and instance.status == 'pending':
        target_url = reverse('dashboard:post_detail', kwargs={'pk': instance.id})
        Notification.objects.create(
            title="New Post Requires Review",
            message=f"'{instance.title}' was submitted and is pending approval.",
            target_url=target_url
        )
