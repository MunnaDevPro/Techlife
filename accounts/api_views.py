# accounts/api_views.py
"""
Token management API endpoints:

  GET  /api/account/tokens/         — list the authenticated user's tokens
  POST /api/account/tokens/         — generate a new token
  POST /api/account/tokens/{id}/revoke/ — revoke a specific token

Authentication: session-based (Django login session) so the dashboard can
call these via AJAX if needed, and ordinary external clients use the
Bearer token for content posting (not token management).
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from accounts.models import UserAPIToken
from accounts.serializers import UserAPITokenSafeSerializer, UserAPITokenCreateResponseSerializer


class UserAPITokenListCreateView(APIView):
    """
    GET  — list the authenticated user's API tokens (prefix, name, dates, status).
    POST — generate a new token. Returns the raw token exactly once.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tokens = UserAPIToken.objects.filter(user=request.user).order_by('-created_at')
        serializer = UserAPITokenSafeSerializer(tokens, many=True)
        return Response(serializer.data)

    def post(self, request):
        name = str(request.data.get('name', '')).strip()[:100]

        token_obj, raw_token = UserAPIToken.generate(user=request.user, name=name)

        response_data = {
            'id': token_obj.pk,
            'name': token_obj.name,
            'token_prefix': token_obj.token_prefix,
            'raw_token': raw_token,
            'created_at': token_obj.created_at,
        }
        serializer = UserAPITokenCreateResponseSerializer(data=response_data)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserAPITokenRevokeView(APIView):
    """
    POST /api/account/tokens/{id}/revoke/

    Revokes the specified token.  The token must belong to the authenticated user.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            token_obj = UserAPIToken.objects.get(pk=pk, user=request.user)
        except UserAPIToken.DoesNotExist:
            return Response(
                {'error': 'Token not found or does not belong to your account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not token_obj.is_active or token_obj.revoked_at is not None:
            return Response(
                {'status': 'already_revoked', 'message': 'This token is already revoked.'},
                status=status.HTTP_200_OK,
            )

        token_obj.revoke()
        return Response(
            {'status': 'revoked', 'message': 'Token revoked successfully.'},
            status=status.HTTP_200_OK,
        )
