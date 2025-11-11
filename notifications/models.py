from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Notification(models.Model):
    """
    Notification model for storing system notifications
    """
    NOTIFICATION_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('quote_accepted', 'Quote Accepted'),
        ('quote_rejected', 'Quote Rejected'),
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_overdue', 'Invoice Overdue'),
        ('team_joined', 'Team Member Joined'),
        ('mention', 'Mention'),
        ('ai_insight', 'AI Insight'),
        ('general', 'General'),
    ]

    # Recipient
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Notification content
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='general'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Status
    is_read = models.BooleanField(default=False)

    # Related object (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    # URL link (optional, for directing user to specific page)
    link = models.CharField(max_length=500, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark this notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
