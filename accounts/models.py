# accounts/models.py
import hashlib
import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from .manager import CustomUserManager
import random
from django.conf import settings
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

class CustomUserModel(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    address_line_1 = models.CharField(null=True, blank=True, max_length=100)
    address_line_2 = models.CharField(null=True, blank=True, max_length=100)
    city = models.CharField(blank=True, max_length=20)
    postcode = models.CharField(blank=True, max_length=20)
    country = models.CharField(blank=True, max_length=20)
    mobile = models.CharField(null=True, blank=True, max_length=15)
    profile_picture = ProcessedImageField(
        upload_to="user_profile",
        processors=[ResizeToFill(400, 400)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
        default="user_profile/default_user_profile.png",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    username = None

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    purpose = models.CharField(max_length=20, default="verify")  # verify/reset

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(random.randint(100000, 999999))
        super().save(*args, **kwargs)


class UserAPIToken(models.Model):
    """
    Per-user public API token for posting content from external sites/scripts.

    SECURITY CONTRACT:
      - Raw token is NEVER stored — only SHA-256 hash.
      - The raw token is returned exactly once via generate() and must be shown
        to the user immediately; it cannot be recovered afterwards.
      - Token format: techlife_user_<32 urlsafe random chars>
      - token_prefix stores the first 16 chars (safe to display in UI).
    """

    TOKEN_PREFIX_LABEL = 'techlife_user_'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_tokens',
        verbose_name='Owner',
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Token Label',
        help_text='A memorable label, e.g. "My Portfolio Site"',
    )
    token_prefix = models.CharField(
        max_length=24,
        verbose_name='Token Prefix',
        help_text='First visible chars of the token (safe to display)',
    )
    hashed_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='Hashed Token (SHA-256)',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Leave blank for a non-expiring token',
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User API Token'
        verbose_name_plural = 'User API Tokens'
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        label = self.name or 'Unnamed'
        return f'{label} ({self.token_prefix}...) — {self.user}'

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def _hash_token(cls, raw_token: str) -> str:
        """Return the SHA-256 hex digest of the raw token string."""
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @classmethod
    def generate(cls, user, name=''):
        """
        Create a new UserAPIToken and return (instance, raw_token).
        The raw_token is returned ONCE and is not stored anywhere.
        """
        raw_random = secrets.token_urlsafe(24)   # 32 base64url chars
        raw_token = f'{cls.TOKEN_PREFIX_LABEL}{raw_random}'
        prefix = raw_token[:20]                  # 'techlife_user_XXXXXX' (safe to display)
        hashed = cls._hash_token(raw_token)

        instance = cls.objects.create(
            user=user,
            name=name or '',
            token_prefix=prefix,
            hashed_token=hashed,
        )
        return instance, raw_token

    @classmethod
    def authenticate(cls, raw_token: str):
        """
        Look up a token by hashing it.  Returns the UserAPIToken instance
        if valid and active, otherwise None.
        Does NOT update last_used_at — the caller must do that.
        """
        if not raw_token or not isinstance(raw_token, str):
            return None
        hashed = cls._hash_token(raw_token.strip())
        try:
            return cls.objects.select_related('user').get(
                hashed_token=hashed,
                is_active=True,
                revoked_at__isnull=True,
            )
        except cls.DoesNotExist:
            return None

    def revoke(self):
        """Soft-revoke this token immediately."""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return self.is_active and self.revoked_at is None and not self.is_expired
