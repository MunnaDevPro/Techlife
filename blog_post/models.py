from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
import hashlib
from django.db import models
from django.utils.text import slugify
from accounts.models import CustomUserModel
from tags.models import Tag
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    font_awesome_icon = models.CharField(default="fa-solid fa-layer-group", max_length=100, null=True, blank=True, verbose_name="Fontawesome icon", help_text="e.g: fa-solid fa-layer-group", error_messages="Enter valid class of fontawesome icon")
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
    name = models.CharField(max_length=100, unique=True)
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
        ("published", "Published"),
        ("rejected", "Rejected"),
    )

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    featured_image = models.ImageField(upload_to="blog_images/", null=True, blank=True)
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

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    views = models.PositiveIntegerField(default=0)

    # likes = models.PositiveIntegerField(default=0)

    content_quality = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="blog_posts")

    def save(self, *args, **kwargs):
        # Generate slug
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Generate hash for text content
        raw_content = (self.title + self.description).encode("utf-8")
        self.content_hash = hashlib.md5(raw_content).hexdigest()

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
            img_bytes = self.featured_image.file.read()
            self.image_hash = hashlib.md5(img_bytes).hexdigest()

            if (
                BlogPost.objects.filter(image_hash=self.image_hash)
                .exclude(pk=self.pk)
                .exists()
            ):
                self.status = "pending"
            else:
                self.status = "published"

        super().save(*args, **kwargs)

    @property
    def total_reactions(self):
        return self.reactions.count()

    def reaction_breakdown(self):
        return self.reactions.values("reaction_type").annotate(
            total=models.Count("reaction_type")
        )

    def __str__(self):
        return f"{self.title} created by {self.author}"


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
    additional_image = models.ImageField(
        upload_to="blog_images/additional/", null=True, blank=True
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
    logo_svg = models.TextField()

    def __str__(self):
        return self.name
    




