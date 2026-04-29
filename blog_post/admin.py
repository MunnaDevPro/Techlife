from django import forms
from django.contrib import admin
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from unfold.admin import ModelAdmin
from blog_post.models import (
    Post_view_ip,
    Category,
    BlogPost,
    HomepageConfig,
    Review,
    BlogAdditionalImage,
    Like,
    SubCategory,
    compnay_logo,
)
from django.utils.html import format_html
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin
from .resources import CategoryResource, SubCategoryResource, BlogPostResource, CompanyLogoResource


@admin.register(compnay_logo)
class CompanyLogoAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = CompanyLogoResource
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("logo_preview", "name", "company_image_url_link")
    search_fields = ("name",)

    fieldsets = (
        ("Company Info", {"fields": ("name",)}),
        ("Branding (Logo)", {
            "fields": ("company_image", "company_image_url"),
            "description": "Upload a logo file or provide an external image URL.",
        }),
    )

    def logo_preview(self, obj):
        try:
            if obj.company_image:
                return format_html(
                    '<img src="{}" style="width:50px;height:50px;object-fit:contain;border-radius:4px;border:1px solid #ddd;">',
                    obj.company_image.url
                )
        except Exception:
            pass
        if obj.company_image_url:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;object-fit:contain;border-radius:4px;border:1px solid #ddd;">',
                obj.company_image_url
            )
        return "No Logo"
    logo_preview.short_description = "Logo Preview"

    def company_image_url_link(self, obj):
        if obj.company_image_url:
            return format_html(
                '<a href="{}" target="_blank" style="color:#3b82f6;">View External Link</a>',
                obj.company_image_url
            )
        return "None"
    company_image_url_link.short_description = "External URL"


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    classes = ["collapse"]
    fields = ('name', 'description', 'slug',)
    readonly_fields = ('slug',)


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    classes = ["collapse"]


class BlogAdditionalImageInline(admin.TabularInline):
    model = BlogAdditionalImage
    extra = 1
    classes = ["collapse"]


class BlogPostAdminForm(forms.ModelForm):
    slug = forms.CharField(required=False, disabled=True)
    views = forms.IntegerField(required=False, disabled=True)
    content_hash = forms.CharField(required=False, disabled=True)
    image_hash = forms.CharField(required=False, disabled=True)
    created_at = forms.DateTimeField(required=False, disabled=True)
    updated_at = forms.DateTimeField(required=False, disabled=True)

    class Meta:
        model = BlogPost
        fields = (
            "title",
            "subtitle",
            "slug",
            "category",
            "subcategory",
            "tags",
            "author",
            "status",
            "is_featured",
            "views",
            "featured_image",
            "featured_image_url",
            "description",
            "meta_title",
            "meta_description",
        )
    description = forms.CharField(
        widget=CKEditorUploadingWidget(
            attrs={
                "id": "post_description",
                "rows": 12,
                "class": (
                    "django-ckeditor-widget w-full bg-gray-50 border border-gray-200 "
                    "rounded-xl px-4 py-3 text-[13px] text-gray-800"
                ),
            }
        ),
        required=False,
    )


# ============================================
# CATEGORY ADMIN
# ============================================

@admin.register(Category)
class CategoryAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = CategoryResource
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("-created_at",)
    list_filter = ("created_at",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubCategoryInline]

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "slug", "font_awesome_icon", "description")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


# ============================================
# SUB-CATEGORY ADMIN
# ============================================

@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = SubCategoryResource
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ("name", "category_name", "slug", "created_at")
    search_fields = ("name", "category__name")
    ordering = ("category__name", "name")
    list_filter = ("category", "created_at")
    autocomplete_fields = ("category",)
    prepopulated_fields = {"slug": ("name",)}

    def category_name(self, obj):
        return obj.category.name
    category_name.short_description = "Category"

    fieldsets = (
        ("Basic Information", {
            "fields": ("category", "name", "slug", "description")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


# ============================================
# BLOG POST ADMIN
# ============================================

@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin, ImportExportModelAdmin):
    form = BlogPostAdminForm
    resource_class = BlogPostResource
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = (
        "image_preview", "title", "author", "category",
        "subcategory", "status", "is_featured", "views", "created_at"
    )
    list_filter = ("is_featured", "status", "category", "subcategory", "created_at")
    list_editable = ("is_featured", "status")
    search_fields = ("title", "author__email", "category__name", "subcategory__name")
    ordering = ("-created_at",)
    autocomplete_fields = ("author", "category", "subcategory")
    filter_horizontal = ("tags",)
    inlines = [BlogAdditionalImageInline]
    readonly_fields = (
        "content_hash",
        "image_hash",
        "created_at",
        "updated_at",
    )

    # ✅ FIX: show all posts per page (বা বড় সংখ্যা)
    list_per_page = 50
    show_full_result_count = True

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "title", "subtitle", "category",
                "subcategory", "tags", "author", "status", "is_featured", "views"
            ),
        }),
        ("Media", {
            "fields": ("featured_image", "featured_image_url"),
        }),
        ("Content", {
            "fields": ("description",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",),
        }),
        ("System Info", {
            "fields": ("content_hash", "image_hash", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def image_preview(self, obj):
        """
        ✅ FIX: try/except দিয়ে ImageKit error handle করো।
        featured_image_url থাকলে সেটা দিয়েই image দেখাও।
        এই fix ছাড়া url-only posts admin list এ render হয় না।
        """
        # 1. featured_image file আছে কিনা try করো
        try:
            if obj.featured_image and obj.featured_image.name:
                return format_html(
                    '<img src="{}" style="width:120px;height:60px;object-fit:cover;border-radius:8px;">',
                    obj.featured_image.url
                )
        except Exception:
            pass

        # 2. featured_image_url দিয়ে দেখাও
        if obj.featured_image_url:
            return format_html(
                '<img src="{}" style="width:120px;height:60px;object-fit:cover;border-radius:8px;">',
                obj.featured_image_url
            )

        return format_html('<span style="color:#999;font-size:11px;">No Image</span>')

    image_preview.short_description = "Preview"


# ============================================
# HOMEPAGE CONFIG ADMIN
# ============================================

@admin.register(HomepageConfig)
class HomepageConfigAdmin(ModelAdmin):
    list_display = (
        "order",
        "section_key",
        "title",
        "category",
        "post_count",
        "is_active",
    )
    list_editable = ("order", "post_count", "is_active", "category")
    list_display_links = ("section_key",)
    ordering = ("order",)
    help_text = "Configure what each homepage section shows."


# ============================================
# ADDITIONAL IMAGES ADMIN
# ============================================

@admin.register(BlogAdditionalImage)
class BlogAdditionalImageAdmin(ModelAdmin):
    list_display = ("image_preview", "blog", "additional_image_url")
    search_fields = ("blog__title",)
    autocomplete_fields = ("blog",)
    list_per_page = 20

    def image_preview(self, obj):
        try:
            if obj.additional_image and obj.additional_image.name:
                return format_html(
                    '<img src="{}" style="width:100px;height:70px;object-fit:cover;border-radius:8px;">',
                    obj.additional_image.url
                )
        except Exception:
            pass
        if obj.additional_image_url:
            return format_html(
                '<img src="{}" style="width:100px;height:70px;object-fit:cover;border-radius:8px;">',
                obj.additional_image_url
            )
        return format_html('<span style="color:#999;">No Image</span>')

    image_preview.short_description = "Image"


# ============================================
# REVIEW ADMIN
# ============================================

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


# ============================================
# LIKE ADMIN
# ============================================

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


# ============================================
# VIEW TRACK ADMIN
# ============================================

@admin.register(Post_view_ip)
class PostViewIpAdmin(ModelAdmin):
    list_display = ("post", "user", "ip_address", "viewed_at")
    search_fields = ("post__title", "user__email", "ip_address")
    list_filter = ("viewed_at",)
    ordering = ("-viewed_at",)