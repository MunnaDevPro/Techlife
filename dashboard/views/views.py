from django.shortcuts import render, redirect
from dashboard.permissions import staff_required
from notification.models import Notification

SIDEBAR_MENU = [
    {
        "name": "Overview",
        "icon": "home",
        "url_name": "dashboard:overview",
        "sub_items": [],
    },
    {
        "name": "Content",
        "icon": "file-text",
        "url_name": "dashboard:content_posts",
        "sub_items": [
            {"name": "Posts", "url_name": "dashboard:content_posts"},
            {"name": "Pending Review", "url_name": "dashboard:content_pending"},
            {"name": "Categories", "url_name": "dashboard:content_categories"},
            {"name": "Tags", "url_name": "dashboard:content_tags"},
            {"name": "Homepage Sections", "url_name": "dashboard:content_homepage"},
        ],
    },
    {
        "name": "Forum",
        "icon": "message-square",
        "url_name": "dashboard:forum_questions",
        "sub_items": [
            {"name": "Questions", "url_name": "dashboard:forum_questions"},
            {"name": "Answers", "url_name": "dashboard:forum_answers"},
            {"name": "Reported", "url_name": "dashboard:forum_reported"},
        ],
    },
    {
        "name": "Moderation",
        "icon": "shield-alert",
        "url_name": "dashboard:mod_comments",
        "sub_items": [
            {"name": "Comment Queue", "url_name": "dashboard:mod_comments"},
            {"name": "Flagged", "url_name": "dashboard:mod_flagged"},
            {"name": "Blocked Users", "url_name": "dashboard:mod_blocked"},
        ],
    },
    {
        "name": "Users",
        "icon": "users",
        "url_name": "dashboard:users_all",
        "sub_items": [
            {"name": "All Users", "url_name": "dashboard:users_all"},
            {"name": "Verification Requests", "url_name": "dashboard:users_verification"},
            {"name": "Roles", "url_name": "dashboard:users_roles"},
        ],
    },
    {
        "name": "SEO",
        "icon": "search",
        "url_name": "dashboard:seo_audit",
        "sub_items": [
            {"name": "Meta Audit", "url_name": "dashboard:seo_audit"},
            {"name": "Sitemap Status", "url_name": "dashboard:seo_sitemap"},
            {"name": "Broken Links", "url_name": "dashboard:seo_broken"},
        ],
    },
    {
        "name": "Analytics",
        "icon": "bar-chart-2",
        "url_name": "dashboard:analytics_traffic",
        "sub_items": [
            {"name": "Traffic", "url_name": "dashboard:analytics_traffic"},
            {"name": "Top Posts", "url_name": "dashboard:analytics_posts"},
            {"name": "Author Performance", "url_name": "dashboard:analytics_authors"},
        ],
    },
    {
        "name": "Site Settings",
        "icon": "settings",
        "url_name": "dashboard:settings_ads",
        "sub_items": [
            {"name": "Ads", "url_name": "dashboard:settings_ads"},
            {"name": "Footer", "url_name": "dashboard:settings_footer"},
            {"name": "Maintenance", "url_name": "dashboard:settings_maintenance"},
        ],
    },
    {
        "name": "Notifications",
        "icon": "bell",
        "url_name": "dashboard:notifications",
        "sub_items": [],
    },
]

def get_dashboard_context(request, page_title, active_menu, active_submenu=None):
    unread_notifications = Notification.objects.filter(is_read=False).count()
    return {
        "page_title": page_title,
        "active_menu": active_menu,
        "active_submenu": active_submenu,
        "sidebar_menu": SIDEBAR_MENU,
        "base_template": "dashboard/partial.html" if request.htmx else "dashboard/base.html",
        "unread_notifications": unread_notifications,
    }

# View list:
@staff_required
def overview(request):
    ctx = get_dashboard_context(request, "Overview", "Overview")
    return render(request, "dashboard/overview.html", ctx)

@staff_required
def content_posts(request):
    ctx = get_dashboard_context(request, "Content Posts", "Content", "dashboard:content_posts")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def content_pending(request):
    ctx = get_dashboard_context(request, "Pending Review", "Content", "dashboard:content_pending")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def content_categories(request):
    ctx = get_dashboard_context(request, "Categories", "Content", "dashboard:content_categories")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def content_tags(request):
    ctx = get_dashboard_context(request, "Tags", "Content", "dashboard:content_tags")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def content_homepage(request):
    ctx = get_dashboard_context(request, "Homepage Sections", "Content", "dashboard:content_homepage")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def forum_questions(request):
    ctx = get_dashboard_context(request, "Forum Questions", "Forum", "dashboard:forum_questions")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def forum_answers(request):
    ctx = get_dashboard_context(request, "Forum Answers", "Forum", "dashboard:forum_answers")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def forum_reported(request):
    ctx = get_dashboard_context(request, "Reported Forum Topics", "Forum", "dashboard:forum_reported")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def mod_comments(request):
    ctx = get_dashboard_context(request, "Comment Queue", "Moderation", "dashboard:mod_comments")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def mod_flagged(request):
    ctx = get_dashboard_context(request, "Flagged Content", "Moderation", "dashboard:mod_flagged")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def mod_blocked(request):
    ctx = get_dashboard_context(request, "Blocked Users", "Moderation", "dashboard:mod_blocked")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def users_all(request):
    ctx = get_dashboard_context(request, "All Users", "Users", "dashboard:users_all")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def users_verification(request):
    ctx = get_dashboard_context(request, "User Verification Requests", "Users", "dashboard:users_verification")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def users_roles(request):
    ctx = get_dashboard_context(request, "User Roles & Permissions", "Users", "dashboard:users_roles")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def seo_audit(request):
    ctx = get_dashboard_context(request, "SEO Meta Audit", "SEO", "dashboard:seo_audit")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def seo_sitemap(request):
    ctx = get_dashboard_context(request, "Sitemap Status", "SEO", "dashboard:seo_sitemap")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def seo_broken(request):
    ctx = get_dashboard_context(request, "Broken Link Checker", "SEO", "dashboard:seo_broken")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def analytics_traffic(request):
    ctx = get_dashboard_context(request, "Traffic Analytics", "Analytics", "dashboard:analytics_traffic")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def analytics_posts(request):
    ctx = get_dashboard_context(request, "Top Performing Posts", "Analytics", "dashboard:analytics_posts")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def analytics_authors(request):
    ctx = get_dashboard_context(request, "Author Performance", "Analytics", "dashboard:analytics_authors")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def settings_ads(request):
    ctx = get_dashboard_context(request, "Ad Settings", "Site Settings", "dashboard:settings_ads")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def settings_footer(request):
    ctx = get_dashboard_context(request, "Footer Management", "Site Settings", "dashboard:settings_footer")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def settings_maintenance(request):
    ctx = get_dashboard_context(request, "Maintenance Mode", "Site Settings", "dashboard:settings_maintenance")
    return render(request, "dashboard/placeholder.html", ctx)

@staff_required
def notifications(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        notification_ids = request.POST.getlist('notification_ids')
        
        if action == 'delete' and notification_ids:
            Notification.objects.filter(id__in=notification_ids).delete()
        
        return redirect('dashboard:notifications')

    # Mark all unread notifications as read
    Notification.objects.filter(is_read=False).update(is_read=True)
    
    notifications_list = Notification.objects.all().order_by('-created_at')[:50]
    
    ctx = get_dashboard_context(request, "Notifications Center", "Notifications")
    ctx["notifications_list"] = notifications_list
    
    return render(request, "dashboard/notifications.html", ctx)
