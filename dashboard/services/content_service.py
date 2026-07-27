from django.db import transaction
from blog_post.models import BlogPost, Category, SubCategory, HomepageConfig
from tags.models import Tag
from django.core.exceptions import PermissionDenied
from dashboard.permissions import staff_required

def get_posts_queryset():
    return BlogPost.objects.select_related('author', 'category', 'subcategory').prefetch_related('tags').order_by('-created_at')

def approve_post(post_id, user):
    """Approve a pending post, changing status to published."""
    with transaction.atomic():
        post = BlogPost.objects.select_related('author').get(pk=post_id)
        if not (user.is_superuser or user.has_perm('blog_post.change_blogpost', post) or user.has_perm('blog_post.change_blogpost')):
            raise PermissionDenied("You do not have permission to approve this post.")
        post.status = "published"
        post.save(skip_auto_status=True)  # custom save keyword to avoid overriding status
        return post

def reject_post(post_id, user):
    """Reject a pending post."""
    with transaction.atomic():
        post = BlogPost.objects.select_related('author').get(pk=post_id)
        if not (user.is_superuser or user.has_perm('blog_post.change_blogpost', post) or user.has_perm('blog_post.change_blogpost')):
            raise PermissionDenied("You do not have permission to reject this post.")
        post.status = "rejected"
        post.save(skip_auto_status=True)
        return post

def delete_post(post_id, user):
    """Delete a post."""
    with transaction.atomic():
        post = BlogPost.objects.get(pk=post_id)
        if not (user.is_superuser or user.has_perm('blog_post.delete_blogpost', post) or user.has_perm('blog_post.delete_blogpost')):
            raise PermissionDenied("You do not have permission to delete this post.")
        post.delete()

def bulk_approve(post_ids, user):
    """Bulk approve posts."""
    approved_count = 0
    with transaction.atomic():
        for pid in post_ids:
            try:
                approve_post(pid, user)
                approved_count += 1
            except (BlogPost.DoesNotExist, PermissionDenied):
                continue
    return approved_count

def bulk_reject(post_ids, user):
    """Bulk reject posts."""
    rejected_count = 0
    with transaction.atomic():
        for pid in post_ids:
            try:
                reject_post(pid, user)
                rejected_count += 1
            except (BlogPost.DoesNotExist, PermissionDenied):
                continue
    return rejected_count

def bulk_delete(post_ids, user):
    """Bulk delete posts."""
    deleted_count = 0
    with transaction.atomic():
        for pid in post_ids:
            try:
                delete_post(pid, user)
                deleted_count += 1
            except (BlogPost.DoesNotExist, PermissionDenied):
                continue
    return deleted_count
