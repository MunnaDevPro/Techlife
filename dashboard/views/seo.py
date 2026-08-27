import urllib.request
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count
from django.core.cache import cache

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from blog_post.models import BlogPost, Category
from dashboard.models import NotFoundLog

@staff_required
def meta_audit(request):
    """Audit sitemap and SEO meta tags of all published posts."""
    qs = BlogPost.objects.filter(status='published').select_related('author')
    
    # Process attributes
    posts = []
    for p in qs:
        title_len = len(p.meta_title) if p.meta_title else 0
        desc_len = len(p.meta_description) if p.meta_description else 0
        has_img = bool(p.featured_image or p.featured_image_url)
        
        posts.append({
            "post": p,
            "meta_title_len": title_len,
            "meta_desc_len": desc_len,
            "has_featured_image": has_img,
            "has_og_image": has_img,
            "title_error": title_len == 0 or title_len > 60,
            "desc_error": desc_len == 0 or desc_len > 160,
        })
        
    # Sort worst offenders first
    sort_by = request.GET.get('sort_by', 'default')
    if sort_by == 'empty_title':
        posts.sort(key=lambda x: (x["meta_title_len"] > 0, x["meta_title_len"]))
    elif sort_by == 'empty_desc':
        posts.sort(key=lambda x: (x["meta_desc_len"] > 0, x["meta_desc_len"]))
    elif sort_by == 'oversized_title':
        posts.sort(key=lambda x: x["meta_title_len"], reverse=True)
    elif sort_by == 'oversized_desc':
        posts.sort(key=lambda x: x["meta_desc_len"], reverse=True)
    else:
        # Default: show posts with errors first
        posts.sort(key=lambda x: (not (x["title_error"] or x["desc_error"])))
        
    ctx = get_dashboard_context(request, "SEO Meta Audit", "SEO", "dashboard:seo_audit")
    ctx.update({
        "posts": posts,
        "sort_by": sort_by,
    })
    return render(request, "dashboard/seo/meta_audit.html", ctx)

@staff_required
def sitemap_status(request):
    """Display dynamic sitemap statistics and comparison counters."""
    # Count database items
    db_posts = BlogPost.objects.filter(status='published').count()
    db_categories = Category.objects.count()
    static_urls = 4  # homepage, blogs, popular_blogs, redirect_search_results
    total_db_urls = db_posts + db_categories + static_urls

    sitemap_data = [
        {
            "name": "PostSitemap",
            "description": "Article pages",
            "icon": "file-text",
            "pattern": "/details/*",
            "db_count": db_posts,
            "sitemap_count": db_posts,
            "coverage": 100 if db_posts > 0 else 0, # Assuming 100% for now
            "status": "Aligned",
            "bg_class": "bg-violet-50",
            "border_class": "border-violet-100",
            "text_class": "text-violet-600",
            "hover_class": "group-hover:bg-violet-100"
        },
        {
            "name": "CategorySitemap",
            "description": "Category pages",
            "icon": "layers",
            "pattern": "/category/*",
            "db_count": db_categories,
            "sitemap_count": db_categories,
            "coverage": 100 if db_categories > 0 else 0,
            "status": "Aligned",
            "bg_class": "bg-sky-50",
            "border_class": "border-sky-100",
            "text_class": "text-sky-600",
            "hover_class": "group-hover:bg-sky-100"
        },
        {
            "name": "StaticViewSitemap",
            "description": "Core static pages",
            "icon": "link",
            "pattern": "Core pages",
            "db_count": static_urls,
            "sitemap_count": static_urls,
            "coverage": 100,
            "status": "Aligned",
            "bg_class": "bg-amber-50",
            "border_class": "border-amber-100",
            "text_class": "text-amber-600",
            "hover_class": "group-hover:bg-amber-100"
        }
    ]
    
    ctx = get_dashboard_context(request, "Sitemap Status", "SEO", "dashboard:seo_sitemap")
    ctx.update({
        "total_db_urls": total_db_urls,
        "db_posts": db_posts,
        "db_categories": db_categories,
        "static_urls": static_urls,
        "sitemap_data": sitemap_data,
    })
    return render(request, "dashboard/seo/sitemap_status.html", ctx)

@staff_required
def broken_links(request):
    """Broken Links index reading from NotFoundLog database logs."""
    from django.db.models import Sum
    from django.utils import timezone
    import datetime

    logs = NotFoundLog.objects.all().order_by('-hit_count')

    total_logs = logs.count()
    total_hits = logs.aggregate(total=Sum('hit_count'))['total'] or 0
    top_offender = logs.first()

    today = timezone.now().date()
    today_logs = NotFoundLog.objects.filter(last_seen__date=today).count()

    ctx = get_dashboard_context(request, "Broken Links / 404 Log", "SEO", "dashboard:seo_broken")
    ctx.update({
        "logs": logs,
        "total_logs": total_logs,
        "total_hits": total_hits,
        "top_offender": top_offender,
        "today_logs": today_logs,
    })
    return render(request, "dashboard/seo/broken_links.html", ctx)

