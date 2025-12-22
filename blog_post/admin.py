from django.contrib import admin
from unfold.admin import ModelAdmin
from blog_post.models import (
    Post_view_ip,
    Category,
    BlogPost,
    Review,
    BlogAdditionalImage,
    Like,
    SubCategory,
    compnay_logo,
)
from django.utils.html import format_html


admin.site.register(compnay_logo)



class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1 
    classes = ["collapse"]
    fields = ('name', 'description', 'slug',)
    readonly_fields = ('slug',)

# Inline classes
class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    classes = ["collapse"]


class BlogAdditionalImageInline(admin.TabularInline):
    model = BlogAdditionalImage
    extra = 1
    classes = ["collapse"]


# CATEGORY ADMIN
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("-created_at",)
    list_filter = ("created_at",)
    
    inlines = [SubCategoryInline]


# --- SUB-CATEGORY ADMIN ---
@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin):
    list_display = ("name", "category_name", "slug", "created_at")
    search_fields = ("name", "category__name")
    ordering = ("category__name", "name")
    list_filter = ("category", "created_at")
    autocomplete_fields = ("category",)

    def category_name(self, obj):
        return obj.category.name
    
    category_name.short_description = "Category"


# BLOG POST ADMIN (main section)
@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    list_display = ("image_preview", "title", "author", "category", "subcategory", "status", "created_at")
    list_filter = ("status", "category", "subcategory", "created_at")
    search_fields = ("title", "author__email", "category__name", "subcategory__name")
    ordering = ("-created_at",)
    inlines = [ReviewInline, BlogAdditionalImageInline]
    readonly_fields = ("content_hash", "image_hash", "created_at", "updated_at")

    fieldsets = (
        ("Basic Info", {
            "fields": ("title", "subtitle", "slug", "category","subcategory", "tags", "author", "status", "views"),
        }),
        ("Media", {
            "fields": ("featured_image", "featured_image_url"),
        }),
        ("Content", {
            "fields": ("description",),
        }),
        ("System Info", {
            "fields": ("content_hash", "image_hash", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    

    def image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="width:120px;height:60px;object-fit:cover;border-radius:8px;">',
                obj.featured_image.url
            )
        elif obj.featured_image_url:
            return format_html(
                '<img src="{}" style="width:120px;height:60px;object-fit:cover;border-radius:8px;">',
                obj.featured_image_url
            )
        return "No Image"


    image_preview.allow_tags = True
    image_preview.short_description = "Preview"


# ADDITIONAL IMAGES ADMIN
@admin.register(BlogAdditionalImage)
class BlogAdditionalImageAdmin(ModelAdmin):
    list_display = ("image_preview", "blog", "additional_image_url")
    search_fields = ("blog__title",)
    autocomplete_fields = ("blog",)
    list_per_page = 20

    def image_preview(self, obj):
        if obj.additional_image:
            return f'<img src="{obj.additional_image.url}" style="width:100px;height:70px;object-fit:cover;border-radius:8px;">'
        elif obj.additional_image_url:
            return f'<img src="{obj.additional_image_url}" style="width:100px;height:70px;object-fit:cover;border-radius:8px;">'
        return "No Image"

    image_preview.allow_tags = True
    image_preview.short_description = "Image"


# REVIEW ADMIN
@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("post", "user", "star_rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("post__title", "user__email")
    autocomplete_fields = ("post", "user")
    ordering = ("-created_at",)

    def star_rating(self, obj):
        return "⭐" * obj.rating

    star_rating.short_description = "Rating"


# LIKE ADMIN
@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ("post_title", "user_email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("post__title", "user__email")
    autocomplete_fields = ("post", "user")
    ordering = ("-created_at",)

    def post_title(self, obj):
        return obj.post.title

    def user_email(self, obj):
        return obj.user.email


# VIEW TRACK ADMIN
@admin.register(Post_view_ip)
class PostViewIpAdmin(ModelAdmin):
    list_display = ("post", "user", "ip_address", "viewed_at")
    search_fields = ("post__title", "user__email", "ip_address")
    list_filter = ("viewed_at",)
    ordering = ("-viewed_at",)



