from django.db import models
from django.conf import settings

# A list of predefined action types for consistency.
# As you build more features, you will add more actions here.
ACTION_TYPES = (
    ('USER_REGISTERED', 'User Registered'),
    ('USER_LOGGED_IN', 'User Logged In'),
    ('COMPANY_CREATED', 'Company Created'),
    ('INVENTORY_ITEM_CREATED', 'Inventory Item Created'),
    ('INVENTORY_ITEM_UPDATED', 'Inventory Item Updated'),
    ('STOCK_LEVEL_ADJUSTED', 'Stock Level Adjusted'),
    ('STOCK_ADDED', 'Stock Added'),
    ('STOCK_REMOVED', 'Stock Removed'),
    ('STOCK_SET', 'Stock Quantity Set'),
    ('STOCK_TRANSFERRED', 'Stock Transferred'),
)

class LogEntry(models.Model):
    """
    Records a significant action taken by a user in the system.
    """
    # Who performed the action?
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,  # Keep the log even if the user is deleted
        null=True, 
        blank=True,
        # --- THE FIX: Add a unique related_name to resolve the clash ---
        related_name='audit_log_entries'
        # -------------------------------------------------------------
    )
    # The company the action is associated with, for multi-tenancy.
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    # What kind of action was it?
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    
    # When did the action occur?
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # A flexible field to store extra details about the event.
    details = models.JSONField(default=dict)

    def __str__(self):
        return f'{self.user} - {self.action_type} at {self.timestamp.strftime("%Y-%m-%d %H:%M")}'