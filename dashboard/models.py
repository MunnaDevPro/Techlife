from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ContentFlag(models.Model):
    REASON_CHOICES = (
        ('spam', 'Spam'),
        ('abuse', 'Abuse'),
        ('offensive', 'Offensive/Harassment'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('resolved', 'Resolved (Removed)'),
        ('dismissed', 'Dismissed (Kept)'),
    )
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_flags')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Flag {self.id} - {self.get_reason_display()} on {self.content_type.model}"

class ModerationLog(models.Model):
    ACTION_CHOICES = (
        ('approve', 'Approve (Dismiss Flag)'),
        ('remove', 'Remove Content'),
        ('ban', 'Ban User'),
        ('unban', 'Unban User'),
    )
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_actions')
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.moderator.email} - {self.get_action_display()} at {self.timestamp}"

class NotFoundLog(models.Model):
    path = models.CharField(max_length=1024, unique=True)
    referer = models.CharField(max_length=1024, blank=True, null=True)
    hit_count = models.PositiveIntegerField(default=1)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"404: {self.path} ({self.hit_count} hits)"

class DailyPostStat(models.Model):
    post = models.ForeignKey('blog_post.BlogPost', on_delete=models.CASCADE, related_name='daily_stats')
    date = models.DateField()
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('post', 'date')

    def __str__(self):
        return f"{self.post.title} on {self.date}"
