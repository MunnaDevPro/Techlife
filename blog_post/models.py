from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
import hashlib
from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
from tags.models import Tag
from django.utils.text import slugify
from imagekit.models import ImageSpecField, ProcessedImageField
from imagekit.processors import ResizeToFill, Adjust, ResizeToFit

class Category(models.Model):
    name = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    font_awesome_icon = models.CharField(default="fa-solid fa-layer-group", max_length=500, null=True, blank=True, verbose_name="Fontawesome icon", help_text="e.g: fa-solid fa-layer-group", error_messages="Enter valid class of fontawesome icon")
    # description = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure the slug is unique
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # While the generated slug exists in the database, keep adding a counter
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Parent Category"
    )
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name_plural = 'SubCategories'
        ordering = ['category__name', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while SubCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class BlogPost(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending Approval"),
        ("edited", "Edited - Pending Approval"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    )

    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True, null=True)
    meta_title = models.CharField(max_length=500, blank=True)
    meta_description = models.CharField(max_length=1000, blank=True)
    slug = models.SlugField(max_length=600, unique=True, blank=True)
    # description = models.TextField()
    description = models.TextField(blank=True, null=True)
    featured_image = ProcessedImageField(
        upload_to="blog_images/",
        processors=[ResizeToFit(1200, 800)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
        max_length=500,
    )
    featured_image_thumbnail = ImageSpecField(
            source='featured_image',
        processors=[ResizeToFill(550,380),Adjust(sharpness=1)],
        format='WEBP',
        options={'quality': 90}
        )

    featured_image_url = models.URLField(max_length=500, null=True, blank=True)

    content_hash = models.CharField(
        max_length=64, editable=False, db_index=True, null=True, blank=True
    )
    image_hash = models.CharField(
        max_length=64, editable=False, db_index=True, null=True, blank=True
    )

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    subcategory = models.ForeignKey(
        SubCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='posts', 
        verbose_name="Sub Category" 
    )
    
    author = models.ForeignKey(CustomUserModel, on_delete=models.CASCADE, related_name='authored_posts')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Featured (Homepage Hero)",
        help_text="Toggle ON to show this post in the homepage carousel/hero section"
    )

    views = models.PositiveIntegerField(default=0)

    # likes = models.PositiveIntegerField(default=0)

    content_quality = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="blog_posts")
    def save(self, *args, **kwargs):
            """
            Custom save method with import support
            """
            # Check if being imported (skip auto status logic during import)
            skip_auto_status = kwargs.pop('skip_auto_status', False)
            
            # Check if this is a new instance
            is_new = self.pk is None
            
            # Generate slug if not provided
            if not self.slug:
                base_slug = slugify(self.title)
                slug = base_slug
                counter = 1
                while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                self.slug = slug

            # Generate hash for text content
            raw_content = (self.title + str(self.description)).encode("utf-8")
            self.content_hash = hashlib.md5(raw_content).hexdigest()

            # Only check duplicates if NOT importing and is new post
            if not skip_auto_status and is_new:
                # If duplicate content exists, prevent auto-publish
                if (
                    BlogPost.objects.filter(content_hash=self.content_hash)
                    .exclude(pk=self.pk)
                    .exists()
                ):
                    self.status = "pending"
                else:
                    self.status = "published"

            # Generate hash for image if uploaded
            if self.featured_image:
                try:
                    self.featured_image.file.seek(0)  # Reset pointer
                    img_bytes = self.featured_image.file.read()
                    self.image_hash = hashlib.md5(img_bytes).hexdigest()
                    self.featured_image.file.seek(0)  # Reset again
                    
                    # Check duplicate image only for new posts (not during import)
                    if not skip_auto_status and is_new:
                        if (
                            BlogPost.objects.filter(image_hash=self.image_hash)
                            .exclude(pk=self.pk)
                            .exists()
                        ):
                            self.status = "pending"
                except Exception as e:
                    print(f"Image hash generation error: {e}")

            super().save(*args, **kwargs)

    @property
    def total_reactions(self):
        """Get total number of reactions"""
        return self.reactions.count()

    def reaction_breakdown(self):
        """Get breakdown of reactions by type"""
        return self.reactions.values("reaction_type").annotate(
            total=models.Count("reaction_type")
        )

    def __str__(self):
        """String representation of the blog post"""
        return f"{self.title} created by {self.author}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'

class Like(models.Model):
    post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(CustomUserModel, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "post",
            "user",
        )  # akta user double like dite parbena 1 ta post er jonno
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.first_name} liked {self.post.title}"


class BlogAdditionalImage(models.Model):
    blog = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name="additional_images"
    )
    additional_image = ProcessedImageField(
        upload_to="blog_images/additional/",
        processors=[ResizeToFit(1200, 800)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
    )
    additional_image_url = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"Image for {self.blog.title}"


class Review(models.Model):
    RATING_CHOICES = (
        (1, " 1 - Very Bad"),
        (2, " 2 - Bad"),
        (3, " 3 - Average"),
        (4, " 4 - Good"),
        (5, " 5 - Excellent"),
    )

    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(CustomUserModel, on_delete=models.CASCADE)

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "post",
            "user",
        )  # akta user double review dite parbena 1 ta post er jonno
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.first_name} rated {self.rating}⭐ on {self.post.title}"

# view count system (Ip tracking)
class Post_view_ip(models.Model):
    post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name="view_track"
    )
    user = models.ForeignKey(
        CustomUserModel, on_delete=models.CASCADE, null=True, blank=True
    )
    ip_address = models.CharField(max_length=255, null=True, blank=True)
    viewed_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "ip_address")

    def __str__(self):
        return f"{self.post.title} viewed by {self.user or self.ip_address}"


class compnay_logo(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    company_image = ProcessedImageField(
        upload_to="company/image",
        processors=[ResizeToFit(800, 800)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
    )
    company_image_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name


class HomepageConfig(models.Model):
    SECTION_KEYS = (
        ('carousel', 'Hero Carousel (Top Featured)'),
        ('blog_grid', 'Blog Grid Section'),
        ('latest_news', 'Latest News Section'),
        ('cat_section_1', 'Category Section 1'),
        ('cat_section_2', 'Category Section 2'),
        ('cat_section_3', 'Category Section 3'),
        ('most_viewed', 'Most Viewed Section'),
    )

    section_key = models.CharField(max_length=50, choices=SECTION_KEYS, unique=True)
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Override section heading (optional)"
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Filter posts by this category (leave blank = all categories)"
    )
    post_count = models.PositiveIntegerField(
        default=6,
        help_text="How many posts to show"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order on homepage"
    )

    class Meta:
        ordering = ['order']
        verbose_name = 'Homepage Section Config'
        verbose_name_plural = 'Homepage Section Configs'

    def __str__(self):
        return f"{self.get_section_key_display()} - {self.category or 'All'} ({self.post_count} posts)"
    




