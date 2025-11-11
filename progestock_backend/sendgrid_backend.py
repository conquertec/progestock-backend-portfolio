"""
Custom Django EMAIL_BACKEND that uses SendGrid API
This allows django-allauth and dj-rest-auth to send emails via SendGrid
"""
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content
import logging
import threading
from functools import wraps

logger = logging.getLogger(__name__)

# Email sending timeout in seconds (prevent hanging requests)
EMAIL_SEND_TIMEOUT = 10


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_decorator(seconds):
    """Decorator to add timeout to a function using threading"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [TimeoutError(f'Function call timed out after {seconds} seconds')]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                # Thread is still running, timed out
                raise TimeoutError(f'Function call timed out after {seconds} seconds')

            if isinstance(result[0], Exception):
                raise result[0]

            return result[0]
        return wrapper
    return decorator

# Email template with logo
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4; }}
        .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
        .header {{ background-color: #3B82F6; padding: 30px 20px; text-align: center; }}
        .logo {{ width: 80px; height: 80px; }}
        .content {{ padding: 30px 20px; color: #333333; line-height: 1.6; }}
        .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666666; }}
        a {{ color: #3B82F6; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <img src="{logo_url}" alt="ProGestock Logo" class="logo">
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>&copy; 2025 ProGestock. All rights reserved.</p>
            <p><a href="https://www.progestock.com">Visit our website</a></p>
        </div>
    </div>
</body>
</html>
"""


class SendGridBackend(BaseEmailBackend):
    """
    Custom email backend that sends emails via SendGrid API.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

        if self.api_key:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None
            logger.warning("SendGridBackend: No SENDGRID_API_KEY found")

    def _wrap_in_template(self, content, is_html=False):
        """Wrap email content in branded template with logo"""
        # Get logo URL from settings or use default
        logo_url = getattr(settings, 'EMAIL_LOGO_URL', 'https://storage.googleapis.com/progestock_bucket/email_logo.png')

        # If content is not HTML, convert line breaks to <br> tags
        if not is_html:
            content = content.replace('\n', '<br>')

        # Wrap in template
        return EMAIL_TEMPLATE.format(logo_url=logo_url, content=content)

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not self.client:
            logger.error("SendGrid client not initialized - cannot send emails")
            return 0

        num_sent = 0
        for message in email_messages:
            try:
                # Create SendGrid Mail object
                sg_mail = Mail(
                    from_email=message.from_email or self.from_email,
                    to_emails=message.to,
                    subject=message.subject
                )

                # Determine if we have HTML content
                has_html = message.content_subtype == 'html'
                html_content = None

                # Check for HTML alternatives
                for alternative in getattr(message, 'alternatives', []):
                    content, mimetype = alternative
                    if mimetype == 'text/html':
                        has_html = True
                        html_content = content
                        break

                if has_html:
                    # Use HTML alternative if available, otherwise use body
                    content_to_wrap = html_content if html_content else message.body
                    wrapped_html = self._wrap_in_template(content_to_wrap, is_html=True)
                    sg_mail.add_content(Content("text/html", wrapped_html))
                else:
                    # Wrap plain text in template
                    wrapped_html = self._wrap_in_template(message.body, is_html=False)
                    sg_mail.add_content(Content("text/plain", message.body))
                    sg_mail.add_content(Content("text/html", wrapped_html))

                # Send via SendGrid API with timeout protection
                try:
                    # Wrap the send call with timeout
                    @timeout_decorator(EMAIL_SEND_TIMEOUT)
                    def send_with_timeout():
                        return self.client.send(sg_mail)

                    response = send_with_timeout()

                    if response.status_code == 202:
                        logger.info(f"Email sent successfully to {message.to[0]}")
                        num_sent += 1
                    else:
                        logger.warning(f"SendGrid returned status {response.status_code} for {message.to[0]}")

                except TimeoutError:
                    logger.error(f"SendGrid timeout sending to {message.to[0]} (exceeded {EMAIL_SEND_TIMEOUT}s)")
                    # Don't re-raise timeout errors - log and continue
                    logger.warning(f"Email sending timed out but continuing registration")

                except Exception as e:
                    logger.error(f"SendGrid error sending to {message.to[0]}: {str(e)}")
                    # Don't re-raise errors - log and continue
                    logger.warning(f"Email sending failed but continuing registration: {str(e)}")

            except Exception as e:
                # Catch any errors during mail object creation
                logger.error(f"Error preparing email for {message.to}: {str(e)}")
                logger.warning(f"Email preparation failed but continuing registration: {str(e)}")

        return num_sent
