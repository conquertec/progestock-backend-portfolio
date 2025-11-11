from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

# This class defines how the User model will be displayed in the admin panel.
class UserAdmin(BaseUserAdmin):
    # These are the fields that will be displayed in the list view of users.
    # We are using 'first_name' and 'last_name' which exist on our model.
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    # These are the fields that can be edited in the admin panel.
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # This is what the admin will search by.
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    # This is necessary when using a custom user model.
    filter_horizontal = ('groups', 'user_permissions',)

# Register your custom User model with the custom UserAdmin configuration.
admin.site.register(User, UserAdmin)
