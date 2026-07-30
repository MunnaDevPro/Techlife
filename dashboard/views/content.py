from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django_tables2 import RequestConfig
from django.db.models import Count

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from dashboard.filters import BlogPostFilter
from dashboard.tables import BlogPostTable
from dashboard.services import content_service
from blog_post.models import BlogPost, Category, SubCategory, HomepageConfig
from tags.models import Tag
from comments.models import Comment
from blog_post.forms import BlogPostForm

# Image validation utility
def validate_featured_image(image):
    if not image:
        return
    # File format check
    valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
    if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
        raise ValidationError("Invalid file type. Only JPG, PNG, and WEBP images are allowed.")
    
    # File size check: 5MB max
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("File size too large. Maximum allowed size is 5MB.")

@staff_required
def post_list(request):
    """List blog posts with filters, pagination, and sorting."""
    qs = content_service.get_posts_queryset()
    filter_set = BlogPostFilter(request.GET, queryset=qs)
    
    table = BlogPostTable(filter_set.qs)
    # Paginate table to 25 items per page
    RequestConfig(request, paginate={"per_page": 25}).configure(table)
    
    ctx = get_dashboard_context(request, "Content Posts", "Content", "dashboard:content_posts")
    ctx.update({
        "table": table,
        "filter": filter_set,
    })
    
    template = "dashboard/content/post_list.html"
    return render(request, template, ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def post_approve(request, pk):
    """Approve a post."""
    try:
        content_service.approve_post(pk, request.user)
        messages.success(request, f"Post approved successfully.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard:content_posts")

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def post_reject(request, pk):
    """Reject a post."""
    try:
        content_service.reject_post(pk, request.user)
        messages.success(request, f"Post rejected successfully.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard:content_posts")

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def post_delete(request, pk):
    """Delete a post."""
    try:
        content_service.delete_post(pk, request.user)
        messages.success(request, f"Post deleted successfully.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("dashboard:content_posts")

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def post_bulk_action(request):
    """Handle bulk status changes and deletions."""
    action = request.POST.get('action')
    post_ids = request.POST.getlist('selection')
    
    if not post_ids:
        messages.warning(request, "No posts selected.")
        return redirect("dashboard:content_posts")
        
    if action == "approve":
        count = content_service.bulk_approve(post_ids, request.user)
        messages.success(request, f"Successfully approved {count} posts.")
    elif action == "reject":
        count = content_service.bulk_reject(post_ids, request.user)
        messages.success(request, f"Successfully rejected {count} posts.")
    elif action == "delete":
        count = content_service.bulk_delete(post_ids, request.user)
        messages.success(request, f"Successfully deleted {count} posts.")
    else:
        messages.error(request, "Invalid action selected.")
        
    return redirect("dashboard:content_posts")

@staff_required
def post_create(request):
    """Dashboard-native view to create a new blog post with full section-by-section layout and SEO integration."""
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        meta_title = request.POST.get('meta_title', '')
        meta_description = request.POST.get('meta_description', '')
        
        if 'featured_image' in request.FILES:
            try:
                validate_featured_image(request.FILES['featured_image'])
            except ValidationError as ve:
                form.add_error('featured_image', ve)
                
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.meta_title = meta_title
            post.meta_description = meta_description
            
            # Status based on superuser/staff approval rules
            if request.user.is_superuser:
                post.status = "published"
            else:
                post.status = "pending"
                
            post.save()
            form.save_m2m() # save tags
            messages.success(request, f"Article '{post.title}' created successfully!")
            return redirect("dashboard:content_posts")
        else:
            messages.error(request, "Failed to create post. Please check errors below.")
    else:
        form = BlogPostForm()
        
    categories = Category.objects.all().order_by('name')
    subcategories = SubCategory.objects.select_related('category').all()
    tags = Tag.objects.all().order_by('name')
    
    ctx = get_dashboard_context(request, "Add New Post", "Content", "dashboard:post_create")
    ctx.update({
        "form": form,
        "categories": categories,
        "subcategories": subcategories,
        "tags": tags,
    })
    return render(request, "dashboard/content/post_create.html", ctx)

@staff_required
def post_detail_edit(request, pk):
    """Tabbed view for post detail / edit."""
    post = get_object_or_404(BlogPost, pk=pk)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.has_perm('blog_post.change_blogpost', post) or request.user.has_perm('blog_post.change_blogpost')):
        raise PermissionDenied("You do not have permission to edit this post.")
        
    if request.method == "POST":
        # Form submittal handles either general, SEO, or media fields
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        meta_title = request.POST.get('meta_title', '')
        meta_description = request.POST.get('meta_description', '')
        
        # Validations on image upload
        if 'featured_image' in request.FILES:
            try:
                validate_featured_image(request.FILES['featured_image'])
            except ValidationError as ve:
                form.add_error('featured_image', ve)
                
        if form.is_valid():
            saved_post = form.save(commit=False)
            saved_post.meta_title = meta_title
            saved_post.meta_description = meta_description
            saved_post.save(skip_auto_status=True)
            messages.success(request, "Post updated successfully.")
            return redirect("dashboard:content_posts")
        else:
            messages.error(request, "Failed to save. Please review the errors below.")
    else:
        form = BlogPostForm(instance=post)
        
    comments = Comment.objects.filter(post=post).select_related('user').order_by('-created_at')
    
    categories = Category.objects.all().order_by('name')
    subcategories = SubCategory.objects.select_related('category').all()
    
    ctx = get_dashboard_context(request, "Edit Post", "Content", "dashboard:content_posts")
    ctx.update({
        "post": post,
        "form": form,
        "comments": comments,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "categories": categories,
        "subcategories": subcategories,
    })
    return render(request, "dashboard/content/post_detail_edit.html", ctx)

@staff_required
@require_POST
def post_comment_delete(request, post_pk, comment_pk):
    """Delete a comment on a post."""
    comment = get_object_or_404(Comment, pk=comment_pk, post_id=post_pk)
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect("dashboard:post_edit", pk=post_pk)

# Categories CRUD
@staff_required
def category_list_crud(request):
    """Simple list & create/delete interface for categories."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "create":
            name = request.POST.get('name')
            icon = request.POST.get('icon', 'fa-solid fa-layer-group')
            desc = request.POST.get('description', '')
            if name:
                Category.objects.create(name=name, font_awesome_icon=icon, description=desc)
                messages.success(request, "Category created successfully.")
            else:
                messages.error(request, "Category name is required.")
        elif action == "delete":
            cat_id = request.POST.get('id')
            get_object_or_404(Category, pk=cat_id).delete()
            messages.success(request, "Category deleted successfully.")
            
        return redirect("dashboard:content_categories")
        
    categories = Category.objects.annotate(post_count=Count('blogpost')).order_by('name')
    ctx = get_dashboard_context(request, "Categories", "Content", "dashboard:content_categories")
    ctx.update({"categories": categories})
    return render(request, "dashboard/content/categories.html", ctx)

# Subcategories CRUD
@staff_required
def subcategory_list_crud(request):
    """CRUD interface for subcategories."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "create":
            category_id = request.POST.get('category_id')
            name = request.POST.get('name')
            desc = request.POST.get('description', '')
            if category_id and name:
                category = get_object_or_404(Category, pk=category_id)
                SubCategory.objects.create(category=category, name=name, description=desc)
                messages.success(request, "Subcategory created.")
            else:
                messages.error(request, "Category and Name are required.")
        elif action == "delete":
            sub_id = request.POST.get('id')
            get_object_or_404(SubCategory, pk=sub_id).delete()
            messages.success(request, "Subcategory deleted.")
            
        return redirect("dashboard:content_subcategories")
        
    subcategories = SubCategory.objects.select_related('category').annotate(post_count=Count('posts')).order_by('category__name', 'name')
    categories = Category.objects.all()
    ctx = get_dashboard_context(request, "Subcategories", "Content", "dashboard:content_subcategories")
    ctx.update({
        "subcategories": subcategories,
        "categories": categories,
    })
    return render(request, "dashboard/content/subcategories.html", ctx)

# Tags CRUD
@staff_required
def tag_list_crud(request):
    """CRUD interface for tags."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "create":
            name = request.POST.get('name')
            if name:
                Tag.objects.get_or_create(name=name)
                messages.success(request, "Tag created successfully.")
            else:
                messages.error(request, "Tag name is required.")
        elif action == "delete":
            tag_id = request.POST.get('id')
            get_object_or_404(Tag, pk=tag_id).delete()
            messages.success(request, "Tag deleted successfully.")
            
        return redirect("dashboard:content_tags")
        
    tags = Tag.objects.annotate(post_count=Count('blog_posts')).order_by('name')
    ctx = get_dashboard_context(request, "Tags", "Content", "dashboard:content_tags")
    ctx.update({"tags": tags})
    return render(request, "dashboard/content/tags.html", ctx)

# Homepage sections CRUD
@staff_required
def homepage_sections(request):
    """Manage HomepageConfig sections (choose categories and post count)."""
    if request.method == "POST":
        config_id = request.POST.get('config_id')
        title = request.POST.get('title', '')
        category_id = request.POST.get('category_id')
        post_count = request.POST.get('post_count', 6)
        is_active = request.POST.get('is_active') == 'true'
        
        cfg = get_object_or_404(HomepageConfig, pk=config_id)
        cfg.title = title
        if category_id:
            cfg.category = get_object_or_404(Category, pk=category_id)
        else:
            cfg.category = None
        cfg.post_count = int(post_count)
        cfg.is_active = is_active
        cfg.save()
        messages.success(request, f"Section '{cfg.get_section_key_display()}' updated.")
        return redirect("dashboard:content_homepage_sections")
        
    configs = HomepageConfig.objects.select_related('category').order_by('order')
    categories = Category.objects.all()
    ctx = get_dashboard_context(request, "Homepage Sections", "Content", "dashboard:content_homepage")
    ctx.update({
        "configs": configs,
        "categories": categories,
    })
    return render(request, "dashboard/content/homepage_sections.html", ctx)
