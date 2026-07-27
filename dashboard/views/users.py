from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import Group

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from accounts.models import CustomUserModel
from blog_post.models import BlogPost
from dashboard.models import ModerationLog

@staff_required
def user_list(request):
    """List all users with verification status, post counts, and joins."""
    qs = CustomUserModel.objects.annotate(post_count=Count('authored_posts')).order_by('-date_joined')
    
    # Filter by verified/unverified status
    verified_filter = request.GET.get('verified')
    if verified_filter == 'true':
        qs = qs.filter(is_verified=True)
    elif verified_filter == 'false':
        qs = qs.filter(is_verified=False)
        
    # Search by email
    search_q = request.GET.get('q', '').strip()
    if search_q:
        qs = qs.filter(email__icontains=search_q)
        
    ctx = get_dashboard_context(request, "All Users", "Users", "dashboard:users_all")
    ctx.update({
        "users": qs,
        "search_q": search_q,
        "verified_filter": verified_filter,
    })
    return render(request, "dashboard/users/user_list.html", ctx)

@staff_required
def user_detail(request, pk):
    """Detail view for a user showing profile info, posts, and role assignments."""
    target_user = get_object_or_404(CustomUserModel, pk=pk)
    
    if request.method == "POST":
        # Block self-permission edits
        if target_user == request.user:
            messages.error(request, "Self-permission escalation is prohibited. You cannot edit your own roles/permissions.")
            return redirect("dashboard:user_detail", pk=pk)
            
        # Extract fields
        is_staff = request.POST.get('is_staff') == 'true'
        is_superuser = request.POST.get('is_superuser') == 'true'
        group_ids = request.POST.getlist('groups')
        
        # Block superuser escalation by non-superusers
        if is_superuser and not request.user.is_superuser:
            raise PermissionDenied("Only superusers can grant superuser privileges.")
            
        # Update user flags
        target_user.is_staff = is_staff
        if request.user.is_superuser:
            target_user.is_superuser = is_superuser
            
        target_user.save()
        
        # Update groups
        groups = Group.objects.filter(id__in=group_ids)
        target_user.groups.set(groups)
        
        # Audit Log
        ModerationLog.objects.create(
            moderator=request.user,
            action='unban',  # Reuse logs or write permission change
            target_user=target_user,
            details=f"Updated permissions: is_staff={is_staff}, is_superuser={target_user.is_superuser}, groups={list(groups.values_list('name', flat=True))}."
        )
        
        messages.success(request, f"User {target_user.email} permissions updated successfully.")
        return redirect("dashboard:user_detail", pk=pk)
        
    # Get user posts
    posts = BlogPost.objects.filter(author=target_user).select_related('category').order_by('-created_at')
    groups = Group.objects.all()
    user_group_ids = list(target_user.groups.values_list('id', flat=True))
    
    ctx = get_dashboard_context(request, "User Detail", "Users", "dashboard:users_all")
    ctx.update({
        "target_user": target_user,
        "posts": posts,
        "groups": groups,
        "user_group_ids": user_group_ids,
    })
    return render(request, "dashboard/users/user_detail.html", ctx)

@staff_required
def verification_requests(request):
    """View unverified users and allow manual verification overrides."""
    unverified_users = CustomUserModel.objects.filter(is_verified=False).order_by('-date_joined')
    
    ctx = get_dashboard_context(request, "Verification Requests", "Users", "dashboard:users_verification")
    ctx.update({
        "users": unverified_users,
    })
    return render(request, "dashboard/users/verification_requests.html", ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def manual_verify_user(request, pk):
    """Verify an unverified user."""
    target_user = get_object_or_404(CustomUserModel, pk=pk, is_verified=False)
    target_user.is_verified = True
    target_user.save()
    
    # Audit log entry
    ModerationLog.objects.create(
        moderator=request.user,
        action='approve',
        target_user=target_user,
        details=f"Manually verified user email {target_user.email}."
    )
    
    messages.success(request, f"User {target_user.email} verified successfully.")
    return redirect("dashboard:users_verification")

@staff_required
def roles_permissions(request):
    """Roles/Permissions index showing Groups and user memberships."""
    groups = Group.objects.annotate(user_count=Count('user')).order_by('name')
    ctx = get_dashboard_context(request, "Roles & Permissions", "Users", "dashboard:users_roles")
    ctx.update({
        "groups": groups,
    })
    return render(request, "dashboard/users/roles.html", ctx)
