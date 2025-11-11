from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = 'Create a superuser from environment variables (for production deployment)'

    def handle(self, *args, **options):
        User = get_user_model()

        # Get credentials from environment variables
        admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        admin_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not admin_email or not admin_password:
            self.stdout.write(
                self.style.WARNING(
                    'Skipping superuser creation: DJANGO_SUPERUSER_EMAIL and/or '
                    'DJANGO_SUPERUSER_PASSWORD environment variables not set.'
                )
            )
            return

        # Check if superuser already exists
        if User.objects.filter(email=admin_email).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser with email {admin_email} already exists.')
            )
            return

        # Create superuser
        try:
            user = User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='User'
            )
            user.is_active = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser: {admin_email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
