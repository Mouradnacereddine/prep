from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'avatar', 'role', 'name']
        read_only_fields = ['id', 'is_staff']

    def get_avatar(self, obj):
        return '/images/placeholder.png'

    def get_role(self, obj):
        return 'Administrateur' if obj.is_staff else 'Utilisateur'

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username