from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FriendRequest, Friendship

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = serializers.SerializerMethodField()

    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'status']  # Exclude 'to_user' field

    def get_from_user(self, obj):
        return {
            'id': obj.from_user.id,
            'username': obj.from_user.username,
            'email': obj.from_user.email,
        }
