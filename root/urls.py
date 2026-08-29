from django.contrib import admin
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, reverse
from django.views.generic import TemplateView
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from blog_post.models import BlogPost, Category

from django.views.static import serve
from django.http import FileResponse
from django.urls import re_path
import os



from django.http import HttpResponse
from django.shortcuts import render

def ads_txt(request):
    return HttpResponse(
        "google.com, pub-7286281628917450, DIRECT, f08c47fec0942fa0",
        content_type="text/plain"
    )

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


def cached_media_serve(request, path):
    """Serve media files with 1-year cache headers."""
    import os
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        from django.http import Http404
        raise Http404("Media file not found")
    response = FileResponse(open(file_path, 'rb'))
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response

class PostSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    protocol = "https"

    def items(self):
        return BlogPost.objects.filter(status="published").order_by("-created_at")

    def lastmod(self, obj):
        return getattr(obj, "updated_at", obj.created_at)

    def location(self, obj):
        return f"/details/{obj.slug}/"


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Category.objects.all().order_by("name")

    def location(self, obj):
        return f"/category/{obj.slug}/"


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return ["homepage", "blogs", "popular_blogs", "redirect_search_results"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "posts": PostSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots"),
    # path("__reload__/", include("django_browser_reload.urls")),  # Temporarily commented - install django-browser-reload
    path("", include("blog_post.urls")),
    path("account/", include("accounts.urls")),
    path("contact/", include("contact.urls")),
    path("forum/", include("forum.urls")),
    
    path('api-auth/', include('rest_framework.urls')),
    path('api/blog/', include('blog_post.api_urls')),
    path('api/account/', include('accounts.api_urls')),

    path("__reload__/", include("django_browser_reload.urls")),
    path('ckeditor/', include('ckeditor_uploader.urls')),

    path('ads.txt', ads_txt),

]

# Serve static files (only needed if whitenoise not in middleware for some reason)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production: serve media files with 1-year cache headers
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', cached_media_serve),
    ]

# Catch-all route to display custom 404 even in debug mode
urlpatterns += [
    re_path(r'^.*$', custom_404),
]

handler404 = 'root.urls.custom_404'