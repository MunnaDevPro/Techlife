from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
import hashlib
from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
from tags.models import Tag
from django.utils.text import slugify
import urllib.parse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from imagekit.models import ImageSpecField, ProcessedImageField
from imagekit.processors import ResizeToFill, Adjust, ResizeToFit


def normalize_url(url):
    if not url:
        return url
    url = url.strip()
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme and not parsed.netloc:
        url = "http://" + url
        parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path
    query = parsed.query
    fragment = parsed.fragment
    return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, query, fragment))

class Category(models.Model):
    name = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    font_awesome_icon = models.CharField(default="layers", max_length=500, null=True, blank=True, verbose_name="Lucide icon name", help_text="e.g: layers, tag, heart")
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
    font_awesome_icon = models.CharField(default="layers", max_length=500, null=True, blank=True, verbose_name="Lucide icon name")

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

    REVIEW_DECISION_CHOICES = (
        ("not_reviewed", "Not Reviewed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
    )

    IMAGE_PROCESSING_STATUS_CHOICES = (
        ("not_started", "Not Started"),
        ("downloaded", "Downloaded"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("placeholder", "Placeholder Used"),
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

    # Source & Automation Metadata
    source_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Source Name", help_text="Original publisher or website name")
    source_url = models.URLField(max_length=500, blank=True, null=True, db_index=True, verbose_name="Source URL", help_text="Original article URL")
    source_author = models.CharField(max_length=255, blank=True, null=True, verbose_name="Source Author", help_text="Original author or reporter name")
    source_published_at = models.DateTimeField(blank=True, null=True, verbose_name="Source Published At", help_text="Original publication timestamp")
    original_title = models.TextField(blank=True, null=True, verbose_name="Original Title", help_text="Original title from source")
    original_content_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True, verbose_name="Original Content Hash", help_text="MD5 hash of original source content")
    automation_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Automation ID", help_text="Unique pipeline execution identifier")
    generated_by_ai = models.BooleanField(default=False, db_index=True, verbose_name="Generated by AI", help_text="Indicates whether content was generated by AI")
    ai_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="AI Model", help_text="AI model identifier used for generation")
    reviewer_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Reviewer Model", help_text="AI model identifier used for automated review")
    review_decision = models.CharField(max_length=20, choices=REVIEW_DECISION_CHOICES, default="not_reviewed", db_index=True, verbose_name="Review Decision")
    quality_score = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Quality Score (0-100)")
    factual_accuracy_score = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Factual Accuracy Score (0-100)")
    language_score = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Language Score (0-100)")
    seo_score = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="SEO Score (0-100)")
    review_notes = models.TextField(blank=True, default="", verbose_name="Review Notes", help_text="Internal reviewer findings or notes")
    source_image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Source Image URL", help_text="Original source image URL")
    image_processing_status = models.CharField(max_length=20, choices=IMAGE_PROCESSING_STATUS_CHOICES, default="not_started", db_index=True, verbose_name="Image Processing Status")
    automation_created_at = models.DateTimeField(blank=True, null=True, verbose_name="Automation Created At", help_text="Timestamp when article was generated by automation")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="blog_posts")

    def clean(self):
        super().clean()
        if self.title:
            raw_content = (self.title + str(self.description or '')).encode("utf-8")
            c_hash = hashlib.md5(raw_content).hexdigest()
            qs = BlogPost.objects.filter(content_hash=c_hash)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("A blog post with duplicate content already exists.")

        if self.featured_image:
            try:
                self.featured_image.file.seek(0)
                img_bytes = self.featured_image.file.read()
                self.featured_image.file.seek(0)
                img_hash = hashlib.md5(img_bytes).hexdigest()
                img_qs = BlogPost.objects.filter(image_hash=img_hash)
                if self.pk:
                    img_qs = img_qs.exclude(pk=self.pk)
                if img_qs.exists():
                    raise ValidationError("A blog post with a duplicate image already exists.")
            except Exception:
                pass

        if self.automation_id and str(self.automation_id).strip():
            self.automation_id = str(self.automation_id).strip()
            auto_qs = BlogPost.objects.filter(automation_id=self.automation_id)
            if self.pk:
                auto_qs = auto_qs.exclude(pk=self.pk)
            if auto_qs.exists():
                raise ValidationError({"automation_id": "A blog post with this Automation ID already exists."})

        scores = {
            "quality_score": self.quality_score,
            "factual_accuracy_score": self.factual_accuracy_score,
            "language_score": self.language_score,
            "seo_score": self.seo_score,
        }
        for field_name, score in scores.items():
            if score is not None and (score < 0 or score > 100):
                raise ValidationError({field_name: f"{field_name.replace('_', ' ').title()} must be between 0 and 100."})

        valid_decisions = [c[0] for c in self.REVIEW_DECISION_CHOICES]
        if self.review_decision and self.review_decision not in valid_decisions:
            raise ValidationError({"review_decision": f"Invalid review decision '{self.review_decision}'."})

        valid_img_statuses = [c[0] for c in self.IMAGE_PROCESSING_STATUS_CHOICES]
        if self.image_processing_status and self.image_processing_status not in valid_img_statuses:
            raise ValidationError({"image_processing_status": f"Invalid image processing status '{self.image_processing_status}'."})

    def save(self, *args, **kwargs):
        """
        Save post preserving explicitly provided status (defaults to 'pending')
        and normalizing source_url.
        """
        kwargs.pop('skip_auto_status', False)

        if self.source_url:
            self.source_url = normalize_url(self.source_url)

        # Generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Default status to pending if not explicitly provided
        if not self.status:
            self.status = "pending"

        # Generate hash for text content
        raw_content = (self.title + str(self.description or '')).encode("utf-8")
        self.content_hash = hashlib.md5(raw_content).hexdigest()

        # Generate hash for image if uploaded
        if self.featured_image:
            try:
                self.featured_image.file.seek(0)
                img_bytes = self.featured_image.file.read()
                self.image_hash = hashlib.md5(img_bytes).hexdigest()
                self.featured_image.file.seek(0)
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


class AutomationPublishLog(models.Model):
    AUTH_SOURCE_CHOICES = (
        ('automation', 'Admin Automation Token'),
        ('user_token', 'User Personal API Token'),
    )

    EVENT_TYPE_CHOICES = (
        ("request_received", "Request Received"),
        ("idempotent_replay", "Idempotent Replay"),
        ("published", "Published"),
        ("rejected", "Rejected"),
        ("conflict", "Conflict"),
        ("throttled", "Throttled"),
        ("disabled", "Disabled"),
        ("processing_failed", "Processing Failed"),
    )

    automation_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    source_name = models.CharField(max_length=255, null=True, blank=True)
    source_url = models.URLField(max_length=1000, null=True, blank=True)
    post = models.ForeignKey(
        'BlogPost',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='automation_logs'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    result_code = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    http_status = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    image_status = models.CharField(max_length=100, null=True, blank=True)
    review_decision = models.CharField(max_length=50, null=True, blank=True)

    quality_score = models.PositiveSmallIntegerField(null=True, blank=True)
    factual_accuracy_score = models.PositiveSmallIntegerField(null=True, blank=True)
    language_score = models.PositiveSmallIntegerField(null=True, blank=True)
    seo_score = models.PositiveSmallIntegerField(null=True, blank=True)

    error_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # ---- User-token specific fields (null for admin automation logs) ----
    auth_source = models.CharField(
        max_length=20,
        choices=AUTH_SOURCE_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Auth Source',
    )
    token_user = models.ForeignKey(
        CustomUserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_token_logs',
        verbose_name='Token Owner',
    )
    token_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='User Token ID',
    )
    source_ip = models.CharField(
        max_length=45,  # IPv6 max length
        null=True,
        blank=True,
        verbose_name='Source IP',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Automation Publish Log'
        verbose_name_plural = 'Automation Publish Logs'
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.automation_id or 'No ID'} ({self.http_status}) - {self.created_at}"

    




