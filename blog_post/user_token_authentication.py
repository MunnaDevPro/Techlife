# blog_post/user_token_authentication.py
"""
DRF authentication class for per-user personal API tokens.

Header format:  Authorization: Bearer <raw_token>

This class is deliberately separate from AutomationAuthentication
(which uses the 'Automation' scheme) so both can coexist in
BlogPostViewSet.authentication_classes without interfering.

Security notes:
  - Returns None for any Authorization header that is not 'Bearer' scheme,
    allowing DRF to fall through to other auth classes.
  - Tokens are looked up by SHA-256 hash only; the raw value is never compared
    directly or stored.
  - Rejected/expired/revoked tokens fail CLOSED (no caching).
  - `last_used_at` is updated atomically via update_fields on success.
"""
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions


class UserAPITokenAuthentication(BaseAuthentication):
    """
    Authenticates requests using  Authorization: Bearer <token>.

    On success:
      - sets request.user  to the token owner
      - sets request.auth  to 'UserAPIToken:<token_pk>'  (so the view can
        extract the token ID for audit logging)
    On failure (bad/revoked/expired token):
      - raises AuthenticationFailed (HTTP 401)
    On non-Bearer header:
      - returns None (let DRF try the next auth class)
    """

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    def authenticate(self, request):
        # Import here to avoid circular imports at module load time
        from accounts.models import UserAPIToken

        auth_header = (
            request.headers.get('Authorization')
            or request.META.get('HTTP_AUTHORIZATION', '')
        )
        if not auth_header:
            return None

        parts = auth_header.strip().split()
        if not parts or parts[0].lower() != 'bearer':
            return None  # Not our scheme; fall through

        if len(parts) != 2 or not parts[1]:
            raise exceptions.AuthenticationFailed(
                'Invalid Bearer authorization header format. '
                'Expected: Authorization: Bearer <token>'
            )

        raw_token = parts[1]

        # Hash and look up — never compare raw tokens
        from accounts.models import UserAPIToken as _UATModel
        hashed = _UATModel._hash_token(raw_token)

        try:
            token_obj = _UATModel.objects.select_related('user').get(
                hashed_token=hashed,
            )
        except _UATModel.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API token.')

        # Fail closed on each request — no stale caching
        if not token_obj.is_active or token_obj.revoked_at is not None:
            raise exceptions.AuthenticationFailed('This API token has been revoked.')

        if token_obj.is_expired:
            raise exceptions.AuthenticationFailed('This API token has expired.')

        user = token_obj.user
        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                'The account associated with this token is inactive.'
            )

        # Update last_used_at without triggering full model save
        _UATModel.objects.filter(pk=token_obj.pk).update(last_used_at=timezone.now())

        # Encode token PK in the auth credential so the view can log it
        return (user, f'UserAPIToken:{token_obj.pk}')
