from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from dashboard.models import ContentFlag, ModerationLog
from accounts.models import CustomUserModel
from comments.models import Comment
from blog_post.models import BlogPost
from forum.models import Question, Answer

def get_next_flagged_item(exclude_ids=None, content_types=None):
    """Retrieves the next pending flag, excluding specific IDs (skipped items)."""
    qs = ContentFlag.objects.filter(status='pending')
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    if content_types:
        qs = qs.filter(content_type__in=content_types)
    return qs.order_by('created_at').first()

def approve_flag(flag_id, moderator):
    """Keep flagged content and dismiss the flag."""
    with transaction.atomic():
        flag = ContentFlag.objects.get(pk=flag_id)
        flag.status = 'dismissed'
        flag.save()
        
        # Log moderation action
        ModerationLog.objects.create(
            moderator=moderator,
            action='approve',
            content_type=flag.content_type,
            object_id=flag.object_id,
            details=f"Dismissed flag ID {flag.id} on {flag.content_type.model} ID {flag.object_id}."
        )

def remove_flagged_content(flag_id, moderator):
    """Remove flagged content or blank it out if it has child relations to avoid cascade deletion."""
    with transaction.atomic():
        flag = ContentFlag.objects.get(pk=flag_id)
        content = flag.content_object
        
        # Log moderation action
        ModerationLog.objects.create(
            moderator=moderator,
            action='remove',
            content_type=flag.content_type,
            object_id=flag.object_id,
            details=f"Resolved flag ID {flag.id} by removing {flag.content_type.model} ID {flag.object_id}."
        )
        
        if flag.content_type.model == 'comment':
            # Check replies child relation
            if content and content.replies.exists():
                content.content = "[This comment has been removed by a moderator]"
                content.save()
            elif content:
                content.delete()
        elif flag.content_type.model == 'question':
            # Check answers child relation
            if content and content.answers.exists():
                content.title = "[Question removed by moderator]"
                content.content = "<p>[This question content has been removed by a moderator]</p>"
                content.save()
            elif content:
                content.delete()
        elif content:
            content.delete()
            
        flag.status = 'resolved'
        flag.save()

def ban_user(user_id, moderator):
    """Deactivate (block) a user."""
    with transaction.atomic():
        user = CustomUserModel.objects.get(pk=user_id)
        user.is_active = False
        user.save()
        
        # Log ban action
        ModerationLog.objects.create(
            moderator=moderator,
            action='ban',
            target_user=user,
            details=f"Banned user email {user.email}."
        )

def unban_user(user_id, moderator):
    """Reactivate (unblock) a user."""
    with transaction.atomic():
        user = CustomUserModel.objects.get(pk=user_id)
        user.is_active = True
        user.save()
        
        # Log unban action
        ModerationLog.objects.create(
            moderator=moderator,
            action='unban',
            target_user=user,
            details=f"Unbanned user email {user.email}."
        )
