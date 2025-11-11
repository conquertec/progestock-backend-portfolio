from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import Notification

User = get_user_model()


def create_notification_for_all_admins(notification_type, title, message, link=None, related_object=None):
    """
    Helper function to create notifications for all admin users
    """
    # Get all admin/staff users
    admin_users = User.objects.filter(is_staff=True)

    for user in admin_users:
        notification_data = {
            'user': user,
            'notification_type': notification_type,
            'title': title,
            'message': message,
            'link': link,
        }

        # Add related object if provided
        if related_object:
            notification_data['content_type'] = ContentType.objects.get_for_model(related_object)
            notification_data['object_id'] = related_object.pk

        Notification.objects.create(**notification_data)


# ========== INVENTORY SIGNALS ==========

@receiver(post_save, sender='inventory.Stock')
def notify_stock_changes(sender, instance, created, **kwargs):
    """
    Create notifications for low stock and out of stock situations
    """
    if created:
        return  # Skip on creation

    # Get the stock status
    from inventory.models import Stock

    # Calculate current quantity
    quantity = instance.quantity

    # Check if product has reorder threshold
    product = instance.product
    reorder_threshold = getattr(product, 'reorder_threshold', 10)

    # Out of stock notification
    if quantity == 0:
        create_notification_for_all_admins(
            notification_type='out_of_stock',
            title=f'Out of Stock Alert',
            message=f"Product '{product.name}' is now out of stock at '{instance.location.name}'.",
            link=f'/stock-control',
            related_object=instance
        )

    # Low stock notification
    elif 0 < quantity <= reorder_threshold:
        create_notification_for_all_admins(
            notification_type='low_stock',
            title=f'Low Stock Warning',
            message=f"Product '{product.name}' is low on stock ({quantity} units remaining) at '{instance.location.name}'.",
            link=f'/stock-control',
            related_object=instance
        )


# ========== SALES SIGNALS ==========

@receiver(post_save, sender='sales.Quote')
def notify_quote_status_change(sender, instance, created, **kwargs):
    """
    Create notifications when quote status changes
    """
    if created:
        return  # Skip on creation

    # Check if status changed to accepted or rejected
    if instance.status == 'ACCEPTED':
        create_notification_for_all_admins(
            notification_type='quote_accepted',
            title='Quote Accepted',
            message=f"Quote #{instance.quote_number} for '{instance.client.name if instance.client else 'Unknown Client'}' has been accepted.",
            link=f'/quotes',
            related_object=instance
        )
    elif instance.status == 'REJECTED':
        create_notification_for_all_admins(
            notification_type='quote_rejected',
            title='Quote Rejected',
            message=f"Quote #{instance.quote_number} for '{instance.client.name if instance.client else 'Unknown Client'}' has been rejected.",
            link=f'/quotes',
            related_object=instance
        )


@receiver(post_save, sender='sales.Invoice')
def notify_invoice_status_change(sender, instance, created, **kwargs):
    """
    Create notifications for invoice payments and overdue invoices
    """
    if created:
        return  # Skip on creation

    # Check if invoice was just paid
    if instance.status == 'PAID' and instance.paid_date:
        # Check if this is a recent change by seeing if paid_date was just set
        from django.utils import timezone
        from datetime import timedelta

        if (timezone.now() - instance.paid_date) < timedelta(minutes=1):
            create_notification_for_all_admins(
                notification_type='invoice_paid',
                title='Invoice Paid',
                message=f"Payment of ${instance.total_amount:.2f} for Invoice #{instance.invoice_number} has been received.",
                link=f'/invoices',
                related_object=instance
            )

    # Check if invoice is overdue
    if instance.status == 'UNPAID' and instance.due_date:
        from django.utils import timezone

        days_overdue = (timezone.now().date() - instance.due_date).days

        if days_overdue > 0:
            # Only create notification once when it becomes overdue
            # Check if we already have an overdue notification for this invoice
            existing_notification = Notification.objects.filter(
                notification_type='invoice_overdue',
                object_id=instance.pk,
                content_type=ContentType.objects.get_for_model(instance)
            ).first()

            if not existing_notification:
                client_name = instance.client.name if instance.client else 'Unknown Client'
                create_notification_for_all_admins(
                    notification_type='invoice_overdue',
                    title='Invoice Overdue',
                    message=f"Invoice #{instance.invoice_number} for '{client_name}' is now {days_overdue} day{'s' if days_overdue != 1 else ''} overdue.",
                    link=f'/invoices',
                    related_object=instance
                )


# ========== TEAM SIGNALS ==========

@receiver(post_save, sender=User)
def notify_new_team_member(sender, instance, created, **kwargs):
    """
    Create notification when a new team member joins
    """
    if created and instance.is_staff:
        # Notify all other admins
        other_admins = User.objects.filter(is_staff=True).exclude(id=instance.id)

        for admin in other_admins:
            Notification.objects.create(
                user=admin,
                notification_type='team_joined',
                title='New Team Member',
                message=f"{instance.get_full_name() or instance.email} has joined the team.",
                link='/settings/team'
            )
