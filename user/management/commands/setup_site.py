from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Setup the Site object for django.contrib.sites'

    def handle(self, *args, **options):
        # Default to Render domain
        site_domain = 'progestock-backend.onrender.com'
        site_name = 'ProGestock'

        # Check if we're in local development
        if settings.DEBUG or 'localhost' in settings.ALLOWED_HOSTS[0]:
            site_domain = 'localhost:8000'
            site_name = 'ProGestock (Local)'
        # Check if we're on Railway
        elif 'RAILWAY_PUBLIC_DOMAIN' in os.environ:
            site_domain = os.environ['RAILWAY_PUBLIC_DOMAIN']
            site_name = 'ProGestock (Railway)'
        elif 'RAILWAY_STATIC_URL' in os.environ:
            site_domain = os.environ['RAILWAY_STATIC_URL'].replace('https://', '').replace('http://', '')
            site_name = 'ProGestock (Railway)'

        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={
                'domain': site_domain,
                'name': site_name
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created Site: {site.name} ({site.domain})')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated Site: {site.name} ({site.domain})')
            )
