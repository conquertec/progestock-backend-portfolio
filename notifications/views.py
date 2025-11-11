from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing notifications

    Endpoints:
    - GET /api/notifications/ - List all notifications for current user
    - GET /api/notifications/{id}/ - Get a specific notification
    - GET /api/notifications/unread_count/ - Get count of unread notifications
    - POST /api/notifications/mark_as_read/ - Mark notification(s) as read
    - POST /api/notifications/mark_all_as_read/ - Mark all notifications as read
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return notifications for the current user only
        """
        user = self.request.user
        queryset = Notification.objects.filter(user=user)

        # Filter by read/unread status
        status_filter = self.request.query_params.get('status', None)
        if status_filter == 'read':
            queryset = queryset.filter(is_read=True)
        elif status_filter == 'unread':
            queryset = queryset.filter(is_read=False)

        # Filter by notification type
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(notification_type=type_filter)

        return queryset

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get the count of unread notifications for the current user
        """
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """
        Mark one or more notifications as read
        Expects: { "notification_ids": [1, 2, 3] }
        """
        notification_ids = request.data.get('notification_ids', [])

        if not notification_ids:
            return Response(
                {'error': 'notification_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        notifications = Notification.objects.filter(
            id__in=notification_ids,
            user=request.user,
            is_read=False
        )

        count = 0
        for notification in notifications:
            notification.mark_as_read()
            count += 1

        return Response({
            'message': f'{count} notification(s) marked as read',
            'count': count
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Mark all notifications as read for the current user
        """
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )

        count = 0
        for notification in notifications:
            notification.mark_as_read()
            count += 1

        return Response({
            'message': f'{count} notification(s) marked as read',
            'count': count
        })

    @action(detail=True, methods=['post'])
    def mark_single_as_read(self, request, pk=None):
        """
        Mark a single notification as read
        """
        notification = self.get_object()

        if notification.user != request.user:
            return Response(
                {'error': 'You do not have permission to modify this notification'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_read()

        return Response({
            'message': 'Notification marked as read',
            'notification': NotificationSerializer(notification).data
        })
