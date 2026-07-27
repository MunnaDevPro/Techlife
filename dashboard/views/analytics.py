import json
from datetime import timedelta
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from blog_post.models import BlogPost, Category
from accounts.models import CustomUserModel
from dashboard.models import DailyPostStat

@staff_required
def traffic_overview(request):
    """Line chart of total daily views over selected range (7, 30, or 90 days)."""
    days = int(request.GET.get('days', 30))
    if days not in [7, 30, 90]:
        days = 30
        
    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    
    # Query database and group by date
    stats = (
        DailyPostStat.objects.filter(date__gte=start_date, date__lte=today)
        .values('date')
        .annotate(total_views=Sum('views_count'))
        .order_by('date')
    )
    
    date_views = {item['date']: item['total_views'] for item in stats}
    labels = []
    values = []
    
    # Fill continuous dates
    for i in range(days + 1):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%b %d'))
        values.append(date_views.get(d, 0) or 0)
        
    ctx = get_dashboard_context(request, "Traffic Analytics", "Analytics", "dashboard:analytics_traffic")
    ctx.update({
        "days": days,
        "chart_labels": json.dumps(labels),
        "chart_values": json.dumps(values),
    })
    return render(request, "dashboard/analytics/traffic.html", ctx)

@staff_required
def top_posts(request):
    """List posts ranked by real views in the selected window, filterable by category."""
    days = int(request.GET.get('days', 30))
    if days not in [7, 30, 90]:
        days = 30
        
    category_id = request.GET.get('category')
    start_date = timezone.now().date() - timedelta(days=days)
    
    posts_qs = BlogPost.objects.filter(status='published')
    if category_id:
        posts_qs = posts_qs.filter(category_id=category_id)
        
    # Sum daily view counts within window range
    posts_qs = (
        posts_qs.filter(daily_stats__date__gte=start_date)
        .annotate(windowed_views=Sum('daily_stats__views_count'))
        .order_by('-windowed_views')
    )
    
    categories = Category.objects.all()
    
    ctx = get_dashboard_context(request, "Top Performing Posts", "Analytics", "dashboard:analytics_posts")
    ctx.update({
        "posts": posts_qs[:50],  # rank top 50
        "categories": categories,
        "selected_category": category_id,
        "days": days,
    })
    return render(request, "dashboard/analytics/top_posts.html", ctx)

@staff_required
def author_performance(request):
    """Aggregate per-author performance within the selected window."""
    days = int(request.GET.get('days', 30))
    if days not in [7, 30, 90]:
        days = 30
        
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Query staff / author users
    authors_qs = CustomUserModel.objects.annotate(
        total_views=Sum(
            'authored_posts__daily_stats__views_count',
            filter=Q(authored_posts__daily_stats__date__gte=start_date)
        ),
        post_count=Count('authored_posts', distinct=True)
    )
    
    # Process avg views
    authors_list = []
    for author in authors_qs:
        views = author.total_views or 0
        posts = author.post_count or 0
        avg_views = round(views / posts, 1) if posts > 0 else 0.0
        
        authors_list.append({
            "author": author,
            "total_views": views,
            "post_count": posts,
            "avg_views": avg_views,
        })
        
    # Handle custom sorting
    sort_by = request.GET.get('sort', 'views')
    if sort_by == 'posts':
        authors_list.sort(key=lambda x: x["post_count"], reverse=True)
    elif sort_by == 'avg':
        authors_list.sort(key=lambda x: x["avg_views"], reverse=True)
    else:
        authors_list.sort(key=lambda x: x["total_views"], reverse=True)
        
    ctx = get_dashboard_context(request, "Author Performance", "Analytics", "dashboard:analytics_authors")
    ctx.update({
        "authors": authors_list,
        "days": days,
        "sort_by": sort_by,
    })
    return render(request, "dashboard/analytics/author_performance.html", ctx)
