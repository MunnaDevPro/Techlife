from django.core.cache import cache
from .models import BlogPost, HomepageConfig


def get_homepage_config(section_key):
    cache_key = f'homepage_config_{section_key}'
    config = cache.get(cache_key)
    if config is None:
        try:
            config = HomepageConfig.objects.select_related('category').get(
                section_key=section_key, is_active=True
            )
        except HomepageConfig.DoesNotExist:
            config = None
        cache.set(cache_key, config, 60 * 5)
    return config


def get_section_posts(section_key, default_count=6, order_by='-created_at'):
    config = get_homepage_config(section_key)
    qs = BlogPost.objects.filter(
        status='published'
    ).select_related('author', 'category').only(
        'id', 'title', 'slug', 'featured_image', 'featured_image_url',
        'created_at', 'views', 'is_featured',
        'author__first_name', 'author__last_name', 'author__email',
        'category__name', 'category__slug',
    )
    if config and config.category:
        qs = qs.filter(category=config.category)
    count = config.post_count if config else default_count
    return list(qs.order_by(order_by)[:count])


def get_carousel_posts():
    config = get_homepage_config('carousel')
    count = config.post_count if config else 6
    qs = BlogPost.objects.filter(
        status='published', is_featured=True
    ).select_related('author', 'category').order_by('-created_at')
    if config and config.category:
        qs = qs.filter(category=config.category)
    posts = list(qs[:count])
    if not posts:
        posts = list(
            BlogPost.objects.filter(status='published')
            .select_related('author', 'category')
            .order_by('-created_at')[:count]
        )
    return posts
from django.core.cache import cache

from .models import BlogPost, HomepageConfig


def get_homepage_config(section_key):
    """Get config for a specific section, with cache."""
    cache_key = f"homepage_config_{section_key}"
    config = cache.get(cache_key)
    if config is None:
        try:
            config = HomepageConfig.objects.select_related("category").get(
                section_key=section_key,
                is_active=True,
            )
        except HomepageConfig.DoesNotExist:
            config = None
        cache.set(cache_key, config, 60 * 5)
    return config


def get_section_posts(section_key, default_count=6, order_by="-created_at"):
    """
    Returns queryset for a section based on its HomepageConfig.
    Falls back to defaults if no config exists.
    """
    config = get_homepage_config(section_key)

    qs = BlogPost.objects.filter(
        status="published",
    ).select_related("author", "category").only(
        "id",
        "title",
        "slug",
        "featured_image",
        "featured_image_url",
        "created_at",
        "views",
        "is_featured",
        "author__first_name",
        "author__last_name",
        "author__email",
        "category__name",
        "category__slug",
    )

    if config and config.category:
        qs = qs.filter(category=config.category)

    count = config.post_count if config else default_count

    return list(qs.order_by(order_by)[:count])


def get_carousel_posts():
    """Featured posts for hero carousel."""
    config = get_homepage_config("carousel")
    count = config.post_count if config else 6

    qs = BlogPost.objects.filter(
        status="published",
        is_featured=True,
    ).select_related("author", "category").order_by("-created_at")

    if config and config.category:
        qs = qs.filter(category=config.category)

    posts = list(qs[:count])

    if not posts:
        posts = list(
            BlogPost.objects.filter(status="published")
            .select_related("author", "category")
            .order_by("-created_at")[:count]
        )
    return posts
