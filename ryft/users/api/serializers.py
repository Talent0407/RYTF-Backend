from dj_rest_auth.models import TokenModel
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer, TokenSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers

from ryft.core.models import Wallet

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "url"]

        extra_kwargs = {"url": {"view_name": "api:user-detail", "lookup_field": "pk"}}


class CustomRegisterSerializer(RegisterSerializer):
    """Use default serializer except don't user username"""

    username = None

    def get_cleaned_data(self):
        return {
            "password1": self.validated_data.get("password1", ""),
            "email": self.validated_data.get("email", ""),
        }


class CustomLoginSerializer(LoginSerializer):
    """Use default serializer except don't user username"""

    username = None


class CustomTokenSerializer(TokenSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = TokenModel
        fields = ("key", "permissions")

    def get_permissions(self, obj: TokenModel):
        wallet = Wallet.objects.get(user=obj.user)
        return {"processed": wallet.processed, "has_access": wallet.has_access}
