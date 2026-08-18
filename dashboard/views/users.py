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
    """List all users and handle creating new admin/staff/general users."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "create":
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            is_staff = request.POST.get('is_staff') == 'true'
            is_verified = request.POST.get('is_verified') == 'true'
            
            if not email or not password:
                messages.error(request, "Email and Password are required.")
            elif CustomUserModel.objects.filter(email=email).exists():
                messages.error(request, "A user with this email already exists.")
            else:
                user = CustomUserModel.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_staff,
                    is_verified=is_verified
                )
                messages.success(request, f"User {user.email} created successfully.")
            return redirect("dashboard:users_all")

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
        form_action = request.POST.get('action')

        if form_action == 'update_profile':
            target_user.first_name = request.POST.get('first_name', target_user.first_name)
            target_user.last_name = request.POST.get('last_name', target_user.last_name)
            target_user.mobile = request.POST.get('mobile', target_user.mobile)
            target_user.city = request.POST.get('city', target_user.city)
            target_user.country = request.POST.get('country', target_user.country)
            
            if 'profile_picture' in request.FILES:
                target_user.profile_picture = request.FILES['profile_picture']
                
            target_user.save()
            messages.success(request, f"User {target_user.email} profile updated successfully.")
            return redirect("dashboard:user_detail", pk=pk)
            
        elif form_action == 'update_permissions':
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
    
    auto_username = getattr(settings, 'TECHLIFE_AUTOMATION_AUTHOR_USERNAME', 'techlife_desk')
    auto_email = auto_username if '@' in auto_username else f"{auto_username}@techlifebd.com"

    ctx = get_dashboard_context(request, "User Detail", "Users", "dashboard:users_all")
    ctx.update({
        "target_user": target_user,
        "posts": posts,
        "groups": groups,
        "user_group_ids": user_group_ids,
        "automation_author_username": auto_username,
        "automation_author_email": auto_email,
        "is_automation_author": (target_user.email.lower() == auto_email.lower() or target_user.email.lower() == auto_username.lower()),
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

@require_POST
@staff_required
def user_delete(request, pk):
    """Delete a user permanently."""
    target_user = get_object_or_404(CustomUserModel, pk=pk)
    
    # Prevent self-deletion
    if target_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("dashboard:users_all")
        
    # Prevent non-superusers from deleting superusers
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only a superuser can delete another superuser.")
        return redirect("dashboard:users_all")
        
    email = target_user.email
    target_user.delete()
    
    # Audit Log
    ModerationLog.objects.create(
        moderator=request.user,
        action='ban', # Closest action to deletion
        details=f"Deleted user account: {email}."
    )
    
    messages.success(request, f"User {email} has been permanently deleted.")
    return redirect("dashboard:users_all")

