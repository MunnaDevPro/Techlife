import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions


class AutomationAuthentication(BaseAuthentication):
    """
    Scoped authentication scheme for automated pipeline tools (e.g., n8n).
    Expects header format: Authorization: Automation <token>
    
    Rules:
    - Requests without the 'Automation' scheme are ignored (return None) to allow standard DRF auth.
    - Timing-safe token comparison using secrets.compare_digest.
    - Resolves target user case-insensitively from settings.TECHLIFE_AUTOMATION_AUTHOR_USERNAME.
    - Rejects missing/inactive/staff/superuser accounts with HTTP 401 AuthenticationFailed.
    - Never logs or returns the secret token.
    """

    def authenticate_header(self, request):
        return 'Automation realm="api"'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.strip().split()
        if not parts or parts[0] != 'Automation':
            return None

        if len(parts) != 2 or not parts[1]:
            raise exceptions.AuthenticationFailed('Invalid automation authorization header format.')

        provided_token = parts[1]
        configured_token = getattr(settings, 'TECHLIFE_AUTOMATION_TOKEN', '')
        if not configured_token or not str(configured_token).strip():
            raise exceptions.AuthenticationFailed('Automation authentication token is not configured on the server.')

        if not secrets.compare_digest(provided_token, str(configured_token).strip()):
            raise exceptions.AuthenticationFailed('Invalid automation token.')

        author_username = getattr(settings, 'TECHLIFE_AUTOMATION_AUTHOR_USERNAME', 'techlife_desk')
        if not author_username or not str(author_username).strip():
            raise exceptions.AuthenticationFailed('Automation author username is not configured on the server.')

        User = get_user_model()
        author_identifier = str(author_username).strip()
        username_field = getattr(User, 'USERNAME_FIELD', 'username')

        if username_field == 'email':
            user = User.objects.filter(email__iexact=author_identifier).first()
            if not user and '@' not in author_identifier:
                user = User.objects.filter(email__iexact=f"{author_identifier}@techlifebd.com").first()
        else:
            user = User.objects.filter(**{f"{username_field}__iexact": author_identifier}).first()

        if not user:
            raise exceptions.AuthenticationFailed('Configured automation author account does not exist.')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('Configured automation author account is inactive.')

        if user.is_staff:
            raise exceptions.AuthenticationFailed('Configured automation author account cannot be a staff member.')

        if user.is_superuser:
            raise exceptions.AuthenticationFailed('Configured automation author account cannot be a superuser.')

        return (user, None)
