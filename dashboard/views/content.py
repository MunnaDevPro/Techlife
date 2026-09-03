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
from dashboard.tables import BlogPostTable, CompanyTable
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
def post_list(request, is_company_view=False):
    """View to display and filter posts (table) with integrated filters, pagination, and bulk actions."""
    # Allow legacy query param fallback
    post_type = request.GET.get('type')
    if post_type == 'company':
        is_company_view = True
        
    filter_set = BlogPostFilter(request.GET, queryset=BlogPost.objects.all().order_by('-created_at'))
    queryset = filter_set.qs
    
    if is_company_view:
        queryset = queryset.filter(is_company=True)
        table = CompanyTable(queryset, request=request)
        page_title = "Companies"
        page_subtitle = "Manage all registered companies on your site"
        add_button_text = "Add New Company"
        item_name_lower = "company"
        item_name_title = "Company"
        base_url_path = "/dashboard/company/"
        bulk_action_url = reverse("dashboard:company_bulk")
    else:
        queryset = queryset.filter(is_company=False)
        table = BlogPostTable(queryset, request=request)
        page_title = "Blog Posts"
        page_subtitle = "Manage, filter and review all your published and pending posts."
        add_button_text = "Add New Post"
        item_name_lower = "post"
        item_name_title = "Post"
        base_url_path = "/dashboard/content/posts/"
        bulk_action_url = reverse("dashboard:post_bulk")

    # Paginate table to 10 items per page
    RequestConfig(request, paginate={"per_page": 10}).configure(table)
    
    ctx = get_dashboard_context(request, page_title, "Content", "dashboard:company_list" if is_company_view else "dashboard:content_posts")
    ctx.update({
        "table": table,
        "filter": filter_set,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "add_button_text": add_button_text,
        "is_company_view": is_company_view,
        "item_name_lower": item_name_lower,
        "item_name_title": item_name_title,
        "base_url_path": base_url_path,
        "bulk_action_url": bulk_action_url,
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
        post = get_object_or_404(BlogPost, pk=pk)
        is_company = post.is_company
        content_service.delete_post(pk, request.user)
        messages.success(request, f"Post deleted successfully.")
        if is_company:
            return redirect(f"{reverse('dashboard:content_posts')}?type=company")
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
        
    referer = request.META.get('HTTP_REFERER', '')
    if 'type=company' in referer:
        return redirect(f"{reverse('dashboard:content_posts')}?type=company")
    return redirect("dashboard:content_posts")

@require_POST
@staff_required
def post_update_status(request, pk):
    """Update a single post's status via modal."""
    post = get_object_or_404(BlogPost, pk=pk)
    status = request.POST.get('status')
    if status in dict(BlogPost.STATUS_CHOICES):
        post.status = status
        post.save(update_fields=['status'])
        messages.success(request, f"Status for '{post.title[:30]}...' updated to {status.title()}.")
    else:
        messages.error(request, "Invalid status selected.")
    return redirect("dashboard:content_posts")

@staff_required
def post_create(request, is_company_view=False):
    """Dashboard-native view to create a new blog post with full section-by-section layout and SEO integration."""
    post_type = request.GET.get('type')
    if post_type == 'company' or is_company_view:
        return redirect("dashboard:company_create")
        
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
            if is_company_view:
                post.is_company = True
            
            # Status based on superuser/staff approval rules
            if request.user.is_superuser:
                post.status = "published"
            else:
                post.status = "pending"
                
            post.save()
            form.save_m2m() # save tags
            messages.success(request, f"Successfully created {'company' if is_company_view else 'article'} '{post.title}'!")
            if is_company_view:
                return redirect("dashboard:company_list")
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
def post_detail(request, pk):
    """View showing full A to Z stats and information of a single post."""
    post = get_object_or_404(BlogPost, pk=pk)
    comments = Comment.objects.filter(post=post).select_related('user').order_by('-created_at')
    
    # Calculate comment analytics
    comments_count = comments.count()
    
    # Gather other statistics
    likes_count = getattr(post, 'likes', None)
    if likes_count is not None:
        likes_count = likes_count.count()
    else:
        likes_count = 0
        
    ctx = get_dashboard_context(request, "Post Details", "Content", "dashboard:content_posts")
    ctx.update({
        "post": post,
        "comments": comments,
        "comments_count": comments_count,
        "likes_count": likes_count,
    })
    return render(request, "dashboard/content/post_detail.html", ctx)

@staff_required
def post_detail_edit(request, pk, is_company_view=False):
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
        subtitle = request.POST.get('subtitle', '')
        
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
            if hasattr(saved_post, 'subtitle'):
                saved_post.subtitle = subtitle
            saved_post.save(skip_auto_status=True)
            form.save_m2m()
            messages.success(request, "Post updated successfully.")
            if saved_post.is_company:
                return redirect(f"{reverse('dashboard:content_posts')}?type=company")
            return redirect("dashboard:content_posts")
        else:
            messages.error(request, "Failed to save. Please review the errors below.")
    else:
        form = BlogPostForm(instance=post)
        
    comments = Comment.objects.filter(post=post).select_related('user').order_by('-created_at')
    
    categories = Category.objects.all().order_by('name')
    subcategories = SubCategory.objects.select_related('category').all()
    tags = Tag.objects.all().order_by('name')
    
    ctx = get_dashboard_context(request, "Edit Post", "Content", "dashboard:content_posts")
    ctx.update({
        "post": post,
        "form": form,
        "comments": comments,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "categories": categories,
        "subcategories": subcategories,
        "tags": tags,
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
            name = request.POST.get('name', '').strip()
            icon = request.POST.get('icon', '').strip() or 'layers'
            desc = request.POST.get('description', '')
            if name:
                if Category.objects.filter(name__iexact=name).exists():
                    messages.error(request, f"Category '{name}' already exists.")
                else:
                    Category.objects.create(name=name, font_awesome_icon=icon, description=desc)
                    messages.success(request, "Category created successfully.")
            else:
                messages.error(request, "Category name is required.")
        elif action == "update":
            cat_id = request.POST.get('id')
            name = request.POST.get('name', '').strip()
            icon = request.POST.get('icon', '').strip() or 'layers'
            desc = request.POST.get('description', '')
            if name:
                if Category.objects.filter(name__iexact=name).exclude(pk=cat_id).exists():
                    messages.error(request, f"Category '{name}' already exists.")
                else:
                    cat = get_object_or_404(Category, pk=cat_id)
                    cat.name = name
                    cat.font_awesome_icon = icon
                    cat.description = desc
                    cat.save()
                    messages.success(request, "Category updated successfully.")
            else:
                messages.error(request, "Category name is required.")
        elif action == "delete":
            cat_id = request.POST.get('id')
            get_object_or_404(Category, pk=cat_id).delete()
            messages.success(request, "Category deleted successfully.")
            
        return redirect("dashboard:content_categories")
        
    categories_qs = Category.objects.annotate(post_count=Count('blogpost')).order_by('name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(categories_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    ctx = get_dashboard_context(request, "Categories", "Content", "dashboard:content_categories")
    ctx.update({
        "categories": page_obj.object_list,
        "page_obj": page_obj,
        "total_categories_count": categories_qs.count(),
    })
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
            icon = request.POST.get('icon', '').strip() or 'layers'
            desc = request.POST.get('description', '')
            if category_id and name:
                category = get_object_or_404(Category, pk=category_id)
                SubCategory.objects.create(category=category, name=name, font_awesome_icon=icon, description=desc)
                messages.success(request, "Subcategory created.")
            else:
                messages.error(request, "Category and Name are required.")
        elif action == "update":
            sub_id = request.POST.get('id')
            category_id = request.POST.get('category_id')
            name = request.POST.get('name', '').strip()
            icon = request.POST.get('icon', '').strip() or 'layers'
            desc = request.POST.get('description', '')
            if sub_id and category_id and name:
                sub = get_object_or_404(SubCategory, pk=sub_id)
                sub.category = get_object_or_404(Category, pk=category_id)
                sub.name = name
                sub.font_awesome_icon = icon
                sub.description = desc
                sub.save()
                messages.success(request, "Subcategory updated.")
            else:
                messages.error(request, "Category and Name are required.")
        elif action == "delete":
            sub_id = request.POST.get('id')
            get_object_or_404(SubCategory, pk=sub_id).delete()
            messages.success(request, "Subcategory deleted.")
            
        return redirect("dashboard:content_subcategories")
        
    subcategories_qs = SubCategory.objects.select_related('category').annotate(post_count=Count('posts')).order_by('category__name', 'name')
    categories = Category.objects.all()
    
    from django.core.paginator import Paginator
    paginator = Paginator(subcategories_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    ctx = get_dashboard_context(request, "Subcategories", "Content", "dashboard:content_subcategories")
    ctx.update({
        "subcategories": page_obj.object_list,
        "categories": categories,
        "page_obj": page_obj,
        "total_subcategories_count": subcategories_qs.count()
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
        
    tags_qs = Tag.objects.annotate(post_count=Count('blog_posts')).order_by('name')
    from django.core.paginator import Paginator
    paginator = Paginator(tags_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    ctx = get_dashboard_context(request, "Tags", "Content", "dashboard:content_tags")
    ctx.update({
        "tags": page_obj.object_list,
        "page_obj": page_obj,
        "total_tags_count": tags_qs.count()
    })
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

import json
from blog_post.forms import CompanyProfileForm
from blog_post.models import CompanyService, CompanyIndustryFocus, CompanyClientFocus, CompanyClient, CompanyLocation

@staff_required
def company_create(request):
    """Multi-step wizard view for creating a company profile."""
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.is_company = True
            if request.user.is_superuser:
                post.status = "published"
            else:
                post.status = "pending"
            post.save()
            form.save_m2m() # save tags
            
            # Process JSON payloads for dynamic models
            try:
                services_data = json.loads(request.POST.get('company_services', '[]'))
                for s in services_data:
                    CompanyService.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage', 0)))
                
                industries_data = json.loads(request.POST.get('company_industries', '[]'))
                for s in industries_data:
                    CompanyIndustryFocus.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage', 0)))
                
                clients_focus_data = json.loads(request.POST.get('company_client_focuses', '[]'))
                for s in clients_focus_data:
                    CompanyClientFocus.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage', 0)))
                
                locations_data = json.loads(request.POST.get('company_locations', '[]'))
                for s in locations_data:
                    CompanyLocation.objects.create(company=post, name=s.get('name'))
                
                clients_data = json.loads(request.POST.get('company_clients', '[]'))
                for s in clients_data:
                    CompanyClient.objects.create(company=post, name=s.get('name'))
            except Exception as e:
                # If json parsing fails, at least the company is saved. We log or ignore.
                pass

            messages.success(request, f"Successfully created company '{post.title}'!")
            return redirect("dashboard:company_list")
        else:
            messages.error(request, "Failed to create company. Please check errors in the form.")
    else:
        form = CompanyProfileForm()

    categories = Category.objects.all().order_by('name')
    subcategories = SubCategory.objects.select_related('category').all()
    
    ctx = get_dashboard_context(request, "Add New Company", "Company Management", "dashboard:company_create")
    ctx.update({
        "form": form,
        "categories": categories,
        "subcategories": subcategories,
    })
    return render(request, "dashboard/content/company_wizard.html", ctx)


@staff_required
def company_detail_edit(request, pk, is_company_view=True):
    """Multi-step wizard view for editing a company profile."""
    post = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.is_company = True
            post.save()
            form.save_m2m() # save tags
            
            # Process JSON payloads for dynamic models
            try:
                # Services
                services_data = json.loads(request.POST.get('company_services', '[]'))
                post.company_services.all().delete()
                for s in services_data:
                    if s.get('name'):
                        CompanyService.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                
                # Industries
                industries_data = json.loads(request.POST.get('company_industries', '[]'))
                post.company_industry_focuses.all().delete()
                for s in industries_data:
                    if s.get('name'):
                        CompanyIndustryFocus.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                
                # Client Focus
                clients_focus_data = json.loads(request.POST.get('company_client_focuses', '[]'))
                post.company_client_focuses.all().delete()
                for s in clients_focus_data:
                    if s.get('name'):
                        CompanyClientFocus.objects.create(company=post, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                
                # Locations
                locations_data = json.loads(request.POST.get('company_locations', '[]'))
                post.company_locations.all().delete()
                for s in locations_data:
                    if s.get('name'):
                        CompanyLocation.objects.create(company=post, name=s.get('name'))
                
                # Clients
                clients_data = json.loads(request.POST.get('company_clients', '[]'))
                post.company_clients.all().delete()
                for s in clients_data:
                    if s.get('name'):
                        CompanyClient.objects.create(company=post, name=s.get('name'))
            except Exception as e:
                pass

            messages.success(request, f"Successfully updated company '{post.title}'!")
            return redirect("dashboard:company_list")
        else:
            messages.error(request, "Failed to update company. Please check errors in the form.")
    else:
        form = CompanyProfileForm(instance=post)

    categories = Category.objects.all().order_by('name')
    subcategories = SubCategory.objects.select_related('category').all()
    
    # Prefetch data for Alpine.js
    services = list(post.company_services.values('name', 'percentage'))
    industries = list(post.company_industry_focuses.values('name', 'percentage'))
    client_focuses = list(post.company_client_focuses.values('name', 'percentage'))
    locations = list(post.company_locations.values('name'))
    clients = list(post.company_clients.values('name'))
    
    ctx = get_dashboard_context(request, "Edit Company", "Company Management", "dashboard:company_edit")
    ctx.update({
        "form": form,
        "post": post,
        "categories": categories,
        "subcategories": subcategories,
        "services_json": json.dumps(services if services else [{"name": "", "percentage": ""}]),
        "industries_json": json.dumps(industries if industries else [{"name": "", "percentage": ""}]),
        "client_focuses_json": json.dumps(client_focuses if client_focuses else [{"name": "", "percentage": ""}]),
        "locations_json": json.dumps(locations if locations else [{"name": ""}]),
        "clients_json": json.dumps(clients if clients else [{"name": ""}]),
        "is_edit_mode": True,
    })
    return render(request, "dashboard/content/company_wizard.html", ctx)
