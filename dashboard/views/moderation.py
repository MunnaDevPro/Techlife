from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from django_ratelimit.decorators import ratelimit

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from dashboard.services import moderation_service
from dashboard.models import ContentFlag
from accounts.models import CustomUserModel

def get_flag_context_data(flag):
    """Formats flag content details for preview display."""
    content_obj = flag.content_object
    content_preview = ""
    
    if not content_obj:
        content_preview = "[Content Already Deleted]"
    elif hasattr(content_obj, 'content'):
        content_preview = content_obj.content
    elif hasattr(content_obj, 'description'):
        content_preview = content_obj.description
    elif hasattr(content_obj, 'message'):
        content_preview = content_obj.message
        
    return {
        "flag": flag,
        "content_type": flag.content_type.model.upper(),
        "reason": flag.get_reason_display(),
        "created_at": flag.created_at,
        "content": content_preview,
        "reporter_email": flag.reported_by.email if flag.reported_by else "Anonymous",
        "note": flag.note,
    }

@staff_required
def moderation_queue(request):
    """Moderation Queue index showing all flagged items one by one."""
    skipped = request.session.get('skipped_flags', [])
    flag = moderation_service.get_next_flagged_item(exclude_ids=skipped)

    pending_count = ContentFlag.objects.filter(status='pending').count()
    total_resolved = ContentFlag.objects.filter(status='resolved').count()
    total_dismissed = ContentFlag.objects.filter(status='dismissed').count()
    skipped_count = len(skipped)

    ctx = get_dashboard_context(request, "Moderation Queue", "Moderation", "dashboard:mod_flagged")
    ctx.update({
        "flag_data": get_flag_context_data(flag) if flag else None,
        "queue_type": "all",
        "pending_count": pending_count,
        "total_resolved": total_resolved,
        "total_dismissed": total_dismissed,
        "skipped_count": skipped_count,
    })
    return render(request, "dashboard/moderation/queue.html", ctx)

@staff_required
def comment_queue(request):
    """Sub-queue showing comments flagged/pending review."""
    from comments.models import Comment
    skipped = request.session.get('skipped_comment_flags', [])
    comment_ct = ContentType.objects.get_for_model(Comment)

    flag = moderation_service.get_next_flagged_item(exclude_ids=skipped, content_types=[comment_ct])

    pending_count = ContentFlag.objects.filter(status='pending', content_type=comment_ct).count()
    total_resolved = ContentFlag.objects.filter(status='resolved', content_type=comment_ct).count()
    total_dismissed = ContentFlag.objects.filter(status='dismissed', content_type=comment_ct).count()
    skipped_count = len(skipped)

    ctx = get_dashboard_context(request, "Comment Queue", "Moderation", "dashboard:mod_comments")
    ctx.update({
        "flag_data": get_flag_context_data(flag) if flag else None,
        "queue_type": "comments",
        "pending_count": pending_count,
        "total_resolved": total_resolved,
        "total_dismissed": total_dismissed,
        "skipped_count": skipped_count,
    })
    return render(request, "dashboard/moderation/queue.html", ctx)

@staff_required
def forum_queue(request):
    """Sub-queue showing reported forum Questions & Answers."""
    from forum.models import Question, Answer
    skipped = request.session.get('skipped_forum_flags', [])
    q_ct = ContentType.objects.get_for_model(Question)
    a_ct = ContentType.objects.get_for_model(Answer)
    
    flag = moderation_service.get_next_flagged_item(exclude_ids=skipped, content_types=[q_ct, a_ct])
    
    pending_count = ContentFlag.objects.filter(status='pending', content_type__in=[q_ct, a_ct]).count()
    total_resolved = ContentFlag.objects.filter(status='resolved', content_type__in=[q_ct, a_ct]).count()
    total_dismissed = ContentFlag.objects.filter(status='dismissed', content_type__in=[q_ct, a_ct]).count()
    skipped_count = len(skipped)

    ctx = get_dashboard_context(request, "Reported Forum Topics", "Forum", "dashboard:forum_reported")
    ctx.update({
        "flag_data": get_flag_context_data(flag) if flag else None,
        "queue_type": "forum",
        "pending_count": pending_count,
        "total_resolved": total_resolved,
        "total_dismissed": total_dismissed,
        "skipped_count": skipped_count,
    })
    return render(request, "dashboard/moderation/queue.html", ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def flag_approve(request, pk, queue_type):
    """Keep content (dismiss flag)."""
    moderation_service.approve_flag(pk, request.user)
    messages.success(request, "Flag dismissed (content kept).")
    
    if queue_type == "comments":
        return redirect("dashboard:mod_comments")
    elif queue_type == "forum":
        return redirect("dashboard:forum_reported")
    return redirect("dashboard:mod_flagged")

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def flag_remove(request, pk, queue_type):
    """Remove content (resolve flag)."""
    moderation_service.remove_flagged_content(pk, request.user)
    messages.success(request, "Flagged content removed successfully.")
    
    if queue_type == "comments":
        return redirect("dashboard:mod_comments")
    elif queue_type == "forum":
        return redirect("dashboard:forum_reported")
    return redirect("dashboard:mod_flagged")

@staff_required
def flag_skip(request, pk, queue_type):
    """Skip item by adding it to session's skip list."""
    session_key = 'skipped_flags'
    if queue_type == "comments":
        session_key = 'skipped_comment_flags'
    elif queue_type == "forum":
        session_key = 'skipped_forum_flags'
        
    skipped = request.session.get(session_key, [])
    if pk not in skipped:
        skipped.append(pk)
        request.session[session_key] = skipped
        request.session.modified = True
        
    messages.info(request, "Skipped item.")
    
    if queue_type == "comments":
        return redirect("dashboard:mod_comments")
    elif queue_type == "forum":
        return redirect("dashboard:forum_reported")
    return redirect("dashboard:mod_flagged")

@staff_required
def reset_skip_list(request, queue_type):
    """Reset session skipped list to re-review skipped items."""
    session_key = 'skipped_flags'
    if queue_type == "comments":
        session_key = 'skipped_comment_flags'
    elif queue_type == "forum":
        session_key = 'skipped_forum_flags'
        
    if session_key in request.session:
        del request.session[session_key]
        messages.success(request, "Skip list reset.")
        
    if queue_type == "comments":
        return redirect("dashboard:mod_comments")
    elif queue_type == "forum":
        return redirect("dashboard:forum_reported")
    return redirect("dashboard:mod_flagged")

@staff_required
def blocked_users(request):
    """List blocked/deactivated users and allow unblocking."""
    from accounts.models import CustomUserModel as UserModel
    users = UserModel.objects.filter(is_active=False).order_by('-date_joined')
    total_blocked = users.count()
    total_active = UserModel.objects.filter(is_active=True).count()
    ctx = get_dashboard_context(request, "Blocked Users", "Moderation", "dashboard:mod_blocked")
    ctx.update({
        "users": users,
        "total_blocked": total_blocked,
        "total_active": total_active,
    })
    return render(request, "dashboard/moderation/blocked_users.html", ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def user_unblock(request, pk):
    """Unblock a deactivated user."""
    moderation_service.unban_user(pk, request.user)
    messages.success(request, "User unblocked successfully.")
    return redirect("dashboard:mod_blocked")
