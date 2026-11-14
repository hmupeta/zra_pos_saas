from rest_framework import serializers
from .models import SignupApplication, TenantInvite


class SignupApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignupApplication
        fields = "__all__"
        read_only_fields = [
            "status", "reviewed_by", "reviewed_at",
            "provisioned_tenant", "admin_username",
        ]


class TenantInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInvite
        fields = "__all__"
        read_only_fields = ["invite_token", "status", "invited_by", "accepted_at"]
