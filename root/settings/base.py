from pathlib import Path
from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-fallback-secret-key-development")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

CONN_MAX_AGE = 60

INSTALLED_APPS = [
    "ckeditor",
    "ckeditor_uploader",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "unfold.contrib.location_field",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "django_extensions",
    "import_export",
    "django_cotton",
    "django_tables2",
    "accounts",
    "blog_post",
    "comments",
    "tags",
    "interactions",
    "notification",
    "earnings",
    "imagekit",
    "rest_framework",
    "maintenance",
    "google_add",
    "contact",
    "forum",
    "site_settings",
    "save_post",
    "django_tailwind_cli",
    "dashboard",
    "integrations",
    "integrations.meta",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "blog_post.middleware.Redirect404Middleware",
    "django_htmx.middleware.HtmxMiddleware",
    "maintenance.middleware.MaintenanceMiddleware",
    "integrations.meta.middleware.MetaPixelMiddleware",
]

ROOT_URLCONF = "root.urls"
WSGI_APPLICATION = "root.wsgi.application"

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://techlife.com.bd",
    "https://www.techlife.com.bd",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blog_post.context_processors.all_category",
                "blog_post.context_processors.timezone_info",
                "blog_post.context_processors.footer_context",
                "forum.context_processors.popular_questions",
                "blog_post.context_processors.follow_stats",
                "forum.context_processors.global_follow_list",
                "google_add.context_processors.google_adds",
                "site_settings.context_processors.site_settings",
                "maintenance.context_processors.maintenance",
                "integrations.meta.context_processors.meta_pixel",
                "notification.context_processors.unread_notifications",
            ],
        },
    },
]

CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"

CKEDITOR_CONFIGS = {
    "default": {
        "allowedContent": True,
        "extraAllowedContent": "script[*]; iframe[*]",
        'versionCheck': False,  # ← এই line টা warning বন্ধ করবে
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Meta / Facebook Pixel + Conversions API (CAPI)
# Leave META_PIXEL_ID empty to disable all tracking automatically.
# META_ACCESS_TOKEN is server-side only — never exposed to frontend.
# ─────────────────────────────────────────────────────────────────────────────
META_PIXEL_ID = config("META_PIXEL_ID", default="")
META_ACCESS_TOKEN = config("META_ACCESS_TOKEN", default="")
META_TEST_EVENT_CODE = config("META_TEST_EVENT_CODE", default="")
META_API_VERSION = config("META_API_VERSION", default="v23.0")

# ─────────────────────────────────────────────────────────────────────────────
# Automation API Credentials & Settings (n8n / Pipeline Publishing)
# ─────────────────────────────────────────────────────────────────────────────
TECHLIFE_AUTOMATION_TOKEN = config("TECHLIFE_AUTOMATION_TOKEN", default="")
TECHLIFE_AUTOMATION_AUTHOR_USERNAME = config("TECHLIFE_AUTOMATION_AUTHOR_USERNAME", default="techlife_desk")
TECHLIFE_AUTOMATION_ENABLED = config("TECHLIFE_AUTOMATION_ENABLED", default=True, cast=bool)
TECHLIFE_AUTOMATION_DAILY_POST_LIMIT = config("TECHLIFE_AUTOMATION_DAILY_POST_LIMIT", default=4, cast=int)
TECHLIFE_AUTOMATION_HOURLY_REQUEST_LIMIT = config("TECHLIFE_AUTOMATION_HOURLY_REQUEST_LIMIT", default=20, cast=int)
TECHLIFE_AUTOMATION_TIMEZONE = config("TECHLIFE_AUTOMATION_TIMEZONE", default="Asia/Dhaka")
AUTOMATION_IMAGE_MAX_BYTES = config("AUTOMATION_IMAGE_MAX_BYTES", default=8388608, cast=int)
AUTOMATION_IMAGE_CONNECT_TIMEOUT = config("AUTOMATION_IMAGE_CONNECT_TIMEOUT", default=5, cast=int)
AUTOMATION_IMAGE_READ_TIMEOUT = config("AUTOMATION_IMAGE_READ_TIMEOUT", default=15, cast=int)
AUTOMATION_IMAGE_MAX_REDIRECTS = config("AUTOMATION_IMAGE_MAX_REDIRECTS", default=3, cast=int)
AUTOMATION_IMAGE_MAX_WIDTH = config("AUTOMATION_IMAGE_MAX_WIDTH", default=1600, cast=int)
AUTOMATION_IMAGE_MAX_HEIGHT = config("AUTOMATION_IMAGE_MAX_HEIGHT", default=1200, cast=int)
AUTOMATION_IMAGE_WEBP_QUALITY = config("AUTOMATION_IMAGE_WEBP_QUALITY", default=82, cast=int)

# ─────────────────────────────────────────────────────────────────────────────
# Per-User API Token Settings
# ─────────────────────────────────────────────────────────────────────────────
TECHLIFE_USER_TOKEN_HOURLY_REQUEST_LIMIT = config("TECHLIFE_USER_TOKEN_HOURLY_REQUEST_LIMIT", default=20, cast=int)
TECHLIFE_USER_TOKEN_DAILY_POST_LIMIT = config("TECHLIFE_USER_TOKEN_DAILY_POST_LIMIT", default=4, cast=int)




REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 5,
}

UNFOLD = {
    "SITE_HEADER": "TechLife Admin Dashboard",
    "RESOURCES": [
        "import_export.resources.ModelResource",
    ],
    "SITE_HEADER_TEXT": "TechLife Admin Dashboard",
    "SITE_TITLE": "TechLife Control Panel",
    "SITE_LOGO": "/static/image/logo-front.PNG",
    "SITE_FAVICON": "/static/image/favicon.ico",
    "SHOW_APP_NAME": True,
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.StaticFilesStorage"
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_MAX_AGE = 31536000

WHITENOISE_MIMETYPES = {
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.CustomUserModel"

# Django Cotton Configurations
COTTON_SNAKE_CASED_NAMES = False
COTTON_ENABLE_CONTEXT_ISOLATION = True



AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

IMAGEKIT_CACHEFILE_DIR = "CACHE/images"
IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = "imagekit.cachefiles.strategies.JustInTime"
IMAGEKIT_DEFAULT_FILE_STORAGE = "default"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

# Celery Configurations
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Dhaka"

# Nightly Scheduler
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'nightly-post-rollup': {
        'task': 'dashboard.tasks.run_compute_daily_rollup',
        'schedule': crontab(hour=1, minute=0),
    },
}

