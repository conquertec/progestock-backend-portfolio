from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model
    """
    time_ago = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'type_display',
            'title',
            'message',
            'is_read',
            'link',
            'created_at',
            'read_at',
            'time_ago',
        ]
        read_only_fields = ['created_at', 'read_at', 'time_ago']

    def get_time_ago(self, obj):
        """
        Return a human-readable time difference
        """
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days} day{"s" if days != 1 else ""} ago'
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return f'{weeks} week{"s" if weeks != 1 else ""} ago'
        else:
            months = diff.days // 30
            return f'{months} month{"s" if months != 1 else ""} ago'
