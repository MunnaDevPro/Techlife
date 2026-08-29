# accounts/serializers.py
"""
DRF serializers for UserAPIToken management endpoints.

Note: hashed_token is NEVER included in any serializer output.
"""
from rest_framework import serializers
from accounts.models import UserAPIToken


class UserAPITokenSafeSerializer(serializers.ModelSerializer):
    """
    Safe list/read serializer.  Never exposes raw or hashed token value.
    """
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = UserAPIToken
        fields = [
            'id',
            'name',
            'token_prefix',
            'is_active',
            'is_expired',
            'created_at',
            'last_used_at',
            'expires_at',
            'revoked_at',
        ]
        read_only_fields = fields

    def get_is_expired(self, obj):
        return obj.is_expired


class UserAPITokenCreateResponseSerializer(serializers.Serializer):
    """
    One-time response after token creation.  Includes the raw token once.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    token_prefix = serializers.CharField()
    raw_token = serializers.CharField(
        help_text='This is the only time this value is returned. Store it securely.'
    )
    created_at = serializers.DateTimeField()
