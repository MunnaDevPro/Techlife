from django.contrib import admin
from django.urls import path, include
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("__reload__/", include("django_browser_reload.urls")),  # Temporarily commented - install django-browser-reload
    path("", include("blog_post.urls")),
    path("account/", include("accounts.urls")),
    path("contact/", include("contact.urls")),
    # path("comment/", include("comments.urls")),
    path("forum/", include("forum.urls")),
    # path("comments/", include("comments.urls")),
    
    path('api-auth/', include('rest_framework.urls')),
    path('api/blog/', include('blog_post.api_urls')),

    path("__reload__/", include("django_browser_reload.urls")),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
