# api_views.py
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator

from .models import (
    Category, SubCategory, BlogPost, BlogAdditionalImage, 
    Like, Review, Post_view_ip, compnay_logo
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, 
    BlogPostListSerializer, BlogPostDetailSerializer,
    BlogPostCreateSerializer, LikeSerializer, ReviewSerializer,
    PostViewIpSerializer, CompanyLogoSerializer
)
from accounts.models import CustomUserModel

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    @method_decorator(cache_page(60*15))  # Cache for 15 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        queryset = SubCategory.objects.all()
        category_slug = self.request.query_params.get('category', None)
        
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        return queryset

class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.filter(status="published")
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BlogPostCreateSerializer
        elif self.action == 'retrieve':
            return BlogPostDetailSerializer
        return BlogPostListSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'like']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        queryset = BlogPost.objects.filter(status="published")
        
        # Filter by category
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by subcategory
        subcategory_slug = self.request.query_params.get('subcategory', None)
        if subcategory_slug:
            queryset = queryset.filter(subcategory__slug=subcategory_slug)
        
        # Filter by author
        author_id = self.request.query_params.get('author', None)
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        # Filter by tag
        tag = self.request.query_params.get('tag', None)
        if tag:
            queryset = queryset.filter(tags__name=tag)
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(subtitle__icontains=search)
            )
        
        # Ordering
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['created_at', '-created_at', 'views', '-views']:
            queryset = queryset.order_by(order_by)
        
        return queryset.select_related('category', 'subcategory', 'author').prefetch_related('tags')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, slug=None):
        blog_post = self.get_object()
        user = request.user
        
        if request.method == 'POST':
            # Like the post
            like, created = Like.objects.get_or_create(
                post=blog_post,
                user=user
            )
            if created:
                return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
            return Response({'status': 'already liked'}, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            # Unlike the post
            try:
                like = Like.objects.get(post=blog_post, user=user)
                like.delete()
                return Response({'status': 'unliked'}, status=status.HTTP_204_NO_CONTENT)
            except Like.DoesNotExist:
                return Response({'error': 'Not liked yet'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def likes(self, request, slug=None):
        blog_post = self.get_object()
        likes = blog_post.likes.all()
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def views(self, request, slug=None):
        blog_post = self.get_object()
        views = Post_view_ip.objects.filter(post=blog_post)
        serializer = PostViewIpSerializer(views, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def record_view(self, request, slug=None):
        blog_post = self.get_object()
        ip_address = self.get_client_ip(request)
        
        # Record view
        view, created = Post_view_ip.objects.get_or_create(
            post=blog_post,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address if not request.user.is_authenticated else None
        )
        
        if created:
            blog_post.views += 1
            blog_post.save()
        
        return Response({'status': 'view recorded'}, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all() 
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Like.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        post_slug = self.request.query_params.get('post', None)
        queryset = Review.objects.all()
        
        if post_slug:
            queryset = queryset.filter(post__slug=post_slug)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CompanyLogoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = compnay_logo.objects.all()
    serializer_class = CompanyLogoSerializer

# Additional API Views
class PopularBlogsAPIView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    
    def get_queryset(self):
        return BlogPost.objects.filter(
            status="published",
            views__gte=100
        ).order_by('-views', '-created_at')[:10]

class LatestBlogsAPIView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    
    def get_queryset(self):
        return BlogPost.objects.filter(status="published").order_by('-created_at')[:10]

class CategoryBlogsAPIView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    
    def get_queryset(self):
        category_slug = self.kwargs.get('slug')
        return BlogPost.objects.filter(
            status="published",
            category__slug=category_slug
        ).order_by('-created_at')

class UserBlogsAPIView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return BlogPost.objects.filter(
            status="published",
            author_id=user_id
        ).order_by('-created_at')