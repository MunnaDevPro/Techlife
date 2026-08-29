# accounts/api_urls.py
from django.urls import path
from accounts.api_views import UserAPITokenListCreateView, UserAPITokenRevokeView

urlpatterns = [
    path('tokens/', UserAPITokenListCreateView.as_view(), name='api_user_tokens'),
    path('tokens/<int:pk>/revoke/', UserAPITokenRevokeView.as_view(), name='api_user_token_revoke'),
]
