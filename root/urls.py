from django.contrib import admin
from django.urls import path, include
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView 
urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'image/company_logo.ico')),

    path("admin/", admin.site.urls),
    # path("__reload__/", include("django_browser_reload.urls")),  # Temporarily commented - install django-browser-reload
    path("", include("blog_post.urls")),
    path("account/", include("accounts.urls")),
    path("contact/", include("contact.urls")),
    path("forum/", include("forum.urls")),
    
    path('api-auth/', include('rest_framework.urls')),
    path('api/blog/', include('blog_post.api_urls')),

    path("__reload__/", include("django_browser_reload.urls")),
    path('ckeditor/', include('ckeditor_uploader.urls')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



