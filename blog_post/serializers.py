# serializers.py
from rest_framework import serializers
from .models import (
    Category, SubCategory, BlogPost, BlogAdditionalImage, 
    Like, Review, Post_view_ip, compnay_logo
)
from accounts.models import CustomUserModel
from tags.models import Tag

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUserModel
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'font_awesome_icon', 
            'description', 'created_at', 'updated_at'
        ]

class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = SubCategory
        fields = [
            'id', 'name', 'slug', 'description', 'category', 
            'category_name', 'created_at', 'updated_at'
        ]

class BlogAdditionalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogAdditionalImage
        fields = ['id', 'additional_image', 'additional_image_url']

class BlogPostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'subtitle', 'slug', 'description', 
            'featured_image', 'featured_image_url', 'category',
            'subcategory', 'author', 'status', 'views', 'likes_count',
            'content_quality', 'created_at', 'updated_at', 'tags',
            'comments_count'
        ]
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_comments_count(self, obj):
        # Assuming you have a comments app
        from comments.models import Comment
        return Comment.objects.filter(post=obj).count()

class BlogPostCreateSerializer(serializers.ModelSerializer):
    tags_list = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'subtitle', 'description', 'featured_image',
            'featured_image_url', 'category', 'subcategory', 'tags_list'
        ]
        read_only_fields = ['author', 'slug', 'status']
    
    def create(self, validated_data):
        tags_list = validated_data.pop('tags_list', [])
        user = self.context['request'].user
        
        # Generate slug
        from django.utils.text import slugify
        title = validated_data.get('title')
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create blog post
        blog_post = BlogPost.objects.create(
            author=user,
            slug=slug,
            **validated_data
        )
        
        # Add tags
        if tags_list:
            tag_objects = []
            for tag_name in tags_list:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name.strip().lower()
                )
                tag_objects.append(tag)
            blog_post.tags.set(tag_objects)
        
        return blog_post
    
    def update(self, instance, validated_data):
        tags_list = validated_data.pop('tags_list', None)
        
        # Update blog post
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update tags if provided
        if tags_list is not None:
            tag_objects = []
            for tag_name in tags_list:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name.strip().lower()
                )
                tag_objects.append(tag)
            instance.tags.set(tag_objects)
        
        instance.save()
        return instance

class BlogPostDetailSerializer(BlogPostListSerializer):
    additional_images = BlogAdditionalImageSerializer(
        many=True, 
        source='additional_images.all',
        read_only=True
    )
    
    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + [
            'additional_images', 'content_hash', 'image_hash'
        ]

class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Like
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['user']

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'post', 'user', 'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['user']

class PostViewIpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post_view_ip
        fields = ['id', 'post', 'user', 'ip_address', 'viewed_at']

class CompanyLogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = compnay_logo
        fields = ['id', 'name', 'logo_svg']