"""
Centralized SendGrid Email Service for Production

This service provides a unified interface for sending emails using SendGrid.
It handles both transactional emails and emails with attachments (PDFs).
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, 
    FileType, Disposition, Content
)
from django.conf import settings
import base64
import logging

logger = logging.getLogger(__name__)


class SendGridEmailService:
    """
    Wrapper for SendGrid email functionality with proper error handling
    and logging for production use.
    """
    
    def __init__(self):
        """Initialize SendGrid client with API key from settings"""
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL

        # Log configuration on startup
        logger.info("=" * 50)
        logger.info("🔧 SendGrid Service Initializing")
        logger.info(f"📧 From Email: {self.from_email}")
        logger.info(f"🔑 API Key Set: {bool(self.api_key)}")
        logger.info(f"🐛 DEBUG Mode: {settings.DEBUG}")
        logger.info(f"🌍 Environment: {'Development' if settings.DEBUG else 'Production'}")

        # Only initialize SendGrid client if API key is provided
        if self.api_key:
            logger.info(f"✅ SendGrid client initialized with key: {self.api_key[:10]}...")
            self.sg = SendGridAPIClient(self.api_key)
        else:
            self.sg = None
            logger.warning("❌ SENDGRID_API_KEY not set. Email sending will fail.")
        logger.info("=" * 50)
    
    def send_email(
        self,
        to_email,
        subject,
        text_content=None,
        html_content=None,
        reply_to=None,
        attachments=None
    ):
        """
        Send an email via SendGrid

        Args:
            to_email (str): Recipient email address
            subject (str): Email subject line
            text_content (str, optional): Plain text content
            html_content (str, optional): HTML content (takes precedence)
            reply_to (str, optional): Reply-to email address
            attachments (list, optional): List of attachment dicts with keys:
                - content (bytes): File content
                - filename (str): File name
                - mimetype (str): MIME type (e.g., 'application/pdf')

        Returns:
            dict: Result with success status and message
        """
        logger.info(f"📧 SendGrid send_email called for: {to_email}")
        logger.info(f"📧 Subject: {subject}")
        logger.info(f"📧 From: {self.from_email}")

        try:
            # Check if SendGrid client is initialized
            if not self.sg:
                error_msg = 'SendGrid API key not configured. Please set SENDGRID_API_KEY environment variable.'
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

            # Validate inputs
            if not to_email:
                return {
                    'success': False,
                    'error': 'No recipient email address provided'
                }

            if not subject:
                return {
                    'success': False,
                    'error': 'No subject provided'
                }

            if not text_content and not html_content:
                return {
                    'success': False,
                    'error': 'No email content provided'
                }
            
            # Create mail object
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject
            )
            
            # Add content (HTML takes precedence)
            if html_content:
                message.add_content(Content("text/html", html_content))
                if text_content:
                    message.add_content(Content("text/plain", text_content))
            elif text_content:
                message.add_content(Content("text/plain", text_content))
            
            # Add reply-to if provided
            if reply_to:
                message.reply_to = reply_to
            
            # Add attachments if provided
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment()
                    
                    # Encode content to base64
                    encoded = base64.b64encode(attachment_data['content']).decode()
                    attachment.file_content = FileContent(encoded)
                    attachment.file_name = FileName(attachment_data['filename'])
                    attachment.file_type = FileType(attachment_data['mimetype'])
                    attachment.disposition = Disposition('attachment')
                    
                    message.add_attachment(attachment)
            
            # Send email
            logger.info(f"📤 Sending email via SendGrid API...")
            response = self.sg.send(message)

            # Log success with detailed info
            logger.info(
                f"✅ SendGrid email sent successfully to {to_email}. "
                f"Status: {response.status_code}, "
                f"Body: {response.body}, "
                f"Headers: {response.headers}"
            )
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}',
                'status_code': response.status_code
            }
            
        except Exception as e:
            # Log error with full details
            logger.error(
                f"❌ SendGrid email failed to {to_email}. "
                f"Error: {str(e)}"
            )
            logger.exception("Full SendGrid error traceback:")

            # Try to extract more details from SendGrid error
            error_detail = str(e)
            if hasattr(e, 'body'):
                error_detail += f" | Body: {e.body}"
            if hasattr(e, 'status_code'):
                error_detail += f" | Status: {e.status_code}"

            return {
                'success': False,
                'error': error_detail
            }
    
    def send_template_email(
        self, 
        to_email, 
        template_id, 
        dynamic_data, 
        reply_to=None
    ):
        """
        Send an email using a SendGrid dynamic template
        
        Args:
            to_email (str): Recipient email address
            template_id (str): SendGrid template ID
            dynamic_data (dict): Dynamic template data
            reply_to (str, optional): Reply-to email address
        
        Returns:
            dict: Result with success status and message
        """
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email
            )
            
            message.template_id = template_id
            message.dynamic_template_data = dynamic_data
            
            if reply_to:
                message.reply_to = reply_to
            
            response = self.sg.send(message)
            
            logger.info(
                f"SendGrid template email sent to {to_email}. "
                f"Template: {template_id}, Status: {response.status_code}"
            )
            
            return {
                'success': True,
                'message': f'Template email sent successfully to {to_email}',
                'status_code': response.status_code
            }
            
        except Exception as e:
            logger.error(
                f"SendGrid template email failed to {to_email}. "
                f"Template: {template_id}, Error: {str(e)}"
            )
            
            return {
                'success': False,
                'error': str(e)
            }


# Global instance for easy import
sendgrid_service = SendGridEmailService()
