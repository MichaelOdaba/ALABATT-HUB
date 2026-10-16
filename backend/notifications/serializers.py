from rest_framework import serializers

from accounts.models import Notification, User


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.user.role != User.Role.MANAGER:
            for field_name in ('user', 'title', 'message', 'notification_type', 'created_at'):
                fields[field_name].read_only = True
        return fields
