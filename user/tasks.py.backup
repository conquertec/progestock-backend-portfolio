from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_verification_email_task(recipient_email, subject, message):
    """
    A Celery task to send an email asynchronously.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return f"Verification email sent to {recipient_email}"
    except Exception as e:
        # Log the error for debugging
        print(f"Failed to send email to {recipient_email}: {e}")
        # You could add more advanced retry logic here if needed


@shared_task
def send_invitation_email_task(recipient_email, invitation_token, company_name, invited_by_name, role):
    """
    A Celery task to send team invitation emails asynchronously.
    """
    try:
        # In production, replace this with your frontend URL
        frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:5173'
        invitation_link = f"{frontend_url}/accept-invitation?token={invitation_token}"

        subject = f"You've been invited to join {company_name} on ProGestock"

        message = f"""
Hello,

{invited_by_name} has invited you to join {company_name} on ProGestock as a {role}.

Click the link below to accept the invitation and set up your account:
{invitation_link}

This invitation will expire in 7 days.

If you believe you received this email in error, you can safely ignore it.

Best regards,
The ProGestock Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return f"Invitation email sent to {recipient_email}"
    except Exception as e:
        print(f"Failed to send invitation email to {recipient_email}: {e}")
        raise
