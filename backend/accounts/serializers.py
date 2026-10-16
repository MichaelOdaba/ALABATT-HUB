from rest_framework import serializers

from .models import AuditLog, User


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'entity', 'entity_id', 'timestamp']
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'category',
            'role',
            'status',
            'is_staff',
            'is_superuser',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_staff', 'is_superuser']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'category',
            'role',
            'status',
        ]
        read_only_fields = ['id', 'role', 'status']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        attrs['role'] = User.Role.MEMBER
        attrs['status'] = User.Status.ACTIVE
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('role', None)
        validated_data.pop('status', None)
        user = User.objects.create_user(password=password, **validated_data)
        user.role = User.Role.MEMBER
        user.status = User.Status.ACTIVE
        user.save(update_fields=['role', 'status'])
        return user
