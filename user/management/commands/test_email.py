"""
Management command to test email sending via SendGrid
Usage: python manage.py test_email your-email@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email sending via configured EMAIL_BACKEND'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send test email to')

    def handle(self, *args, **options):
        recipient_email = options['email']

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.WARNING(f"Testing email to: {recipient_email}"))
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"DEBUG: {settings.DEBUG}")
        self.stdout.write(f"SENDGRID_API_KEY set: {bool(settings.SENDGRID_API_KEY)}")
        self.stdout.write("=" * 70)

        try:
            self.stdout.write(self.style.WARNING("\nSending test email..."))

            num_sent = send_mail(
                subject='ProGestock Email Test',
                message='This is a test email from ProGestock backend. If you received this, email sending is working!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

            self.stdout.write(self.style.SUCCESS(f"\n✅ Email sent successfully!"))
            self.stdout.write(self.style.SUCCESS(f"Number of emails sent: {num_sent}"))
            self.stdout.write(self.style.SUCCESS(f"\nCheck {recipient_email} inbox (and spam folder)!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error sending email: {str(e)}"))
            logger.exception("Full error traceback:")
            raise
