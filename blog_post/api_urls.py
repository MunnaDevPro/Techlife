# api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CategoryViewSet, SubCategoryViewSet, BlogPostViewSet,
    LikeViewSet, ReviewViewSet, CompanyLogoViewSet,
    PopularBlogsAPIView, LatestBlogsAPIView, CategoryBlogsAPIView,
    UserBlogsAPIView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'posts', BlogPostViewSet, basename='post')
router.register(r'likes', LikeViewSet, basename='like')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'company-logos', CompanyLogoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('popular-posts/', PopularBlogsAPIView.as_view(), name='api-popular-posts'),
    path('latest-posts/', LatestBlogsAPIView.as_view(), name='api-latest-posts'),
    path('category/<slug:slug>/posts/', CategoryBlogsAPIView.as_view(), name='api-category-posts'),
    path('user/<int:user_id>/posts/', UserBlogsAPIView.as_view(), name='api-user-posts'),
]