"""
Email service for sending quotes and invoices to clients
"""
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .pdf_generator import generate_quote_pdf, generate_invoice_pdf
from .utils import format_currency
import logging
import requests
from io import BytesIO

logger = logging.getLogger(__name__)


def send_quote_email(quote, recipient_email=None):
    """
    Send quote via email to client with PDF attachment

    Args:
        quote: Quote instance
        recipient_email: Optional email override, defaults to client email

    Returns:
        dict: Result with success/error message
    """
    # Use client email if not specified
    if not recipient_email:
        recipient_email = quote.client.email

    if not recipient_email:
        return {
            'success': False,
            'error': 'No email address available for this client'
        }

    try:
        # Generate PDF
        pdf_data = generate_quote_pdf(quote)

        # Prepare email context
        context = {
            'quote': quote,
            'company': quote.company,
            'client': quote.client,
        }

        # Render email body
        subject = f'Quote {quote.quote_number} from {quote.company.name}'

        # Check if company has a logo for inline attachment
        has_logo = bool(quote.company.logo)

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2563eb;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .company-logo {{
                    max-width: 150px;
                    max-height: 80px;
                    margin-bottom: 10px;
                }}
                .content {{
                    background-color: #f9fafb;
                    padding: 30px;
                    border: 1px solid #e5e7eb;
                }}
                .details {{
                    background-color: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                }}
                .details table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .details td {{
                    padding: 8px 0;
                }}
                .details td:first-child {{
                    font-weight: bold;
                    color: #6b7280;
                    width: 40%;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #2563eb;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {f'<img src="cid:company_logo" alt="{quote.company.name}" class="company-logo" />' if has_logo else ''}
                    <h1>Quotation</h1>
                    <p>{quote.quote_number}</p>
                </div>

                <div class="content">
                    <p>Dear {quote.client.name},</p>

                    <p>Thank you for your interest in our products/services. Please find attached our quotation <strong>{quote.quote_number}</strong> for your review.</p>

                    <div class="details">
                        <table>
                            <tr>
                                <td>Quote Number:</td>
                                <td>{quote.quote_number}</td>
                            </tr>
                            <tr>
                                <td>Date Issued:</td>
                                <td>{quote.date_issued.strftime('%B %d, %Y')}</td>
                            </tr>
                            <tr>
                                <td>Valid Until:</td>
                                <td>{quote.expiration_date.strftime('%B %d, %Y')}</td>
                            </tr>
                            <tr>
                                <td>Total Amount:</td>
                                <td><strong>{format_currency(quote.total_amount, quote.company.currency)}</strong></td>
                            </tr>
                        </table>
                    </div>

                    <p>The complete quotation details are attached as a PDF document. This quote is valid until {quote.expiration_date.strftime('%B %d, %Y')}.</p>

                    {f'<p><strong>Additional Notes:</strong><br/>{quote.notes}</p>' if quote.notes else ''}

                    <p>If you have any questions or would like to proceed with this quote, please don't hesitate to contact us.</p>

                    <p>Best regards,<br/>
                    <strong>{quote.company.name}</strong><br/>
                    {getattr(quote.company, 'email', '') or ''}</p>
                </div>

                <div class="footer">
                    <p>This is an automated email. Please do not reply directly to this message.</p>
                    <p>&copy; {quote.company.name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_message = f"""
        Quotation {quote.quote_number}

        Dear {quote.client.name},

        Thank you for your interest in our products/services. Please find attached our quotation {quote.quote_number} for your review.

        Quote Details:
        - Quote Number: {quote.quote_number}
        - Date Issued: {quote.date_issued.strftime('%B %d, %Y')}
        - Valid Until: {quote.expiration_date.strftime('%B %d, %Y')}
        - Total Amount: {format_currency(quote.total_amount, quote.company.currency)}

        The complete quotation details are attached as a PDF document.

        {f'Additional Notes: {quote.notes}' if quote.notes else ''}

        Best regards,
        {quote.company.name}
        {getattr(quote.company, 'email', '') or ''}
        """

        # Create email
        company_email = getattr(quote.company, 'email', None)
        email = EmailMessage(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
            reply_to=[company_email] if company_email else None,
        )

        # Attach PDF
        email.attach(
            f'Quote-{quote.quote_number}.pdf',
            pdf_data,
            'application/pdf'
        )

        # Set HTML content
        email.content_subtype = 'html'
        email.body = html_message

        # Attach company logo as inline image if it exists
        if quote.company.logo:
            try:
                # Download the logo from GCS
                logo_url = quote.company.logo.url
                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                # Get the file extension
                logo_name = quote.company.logo.name
                ext = logo_name.split('.')[-1] if '.' in logo_name else 'png'

                # Attach as inline image with Content-ID
                from email.mime.image import MIMEImage
                inline_image = MIMEImage(response.content)
                inline_image.add_header('Content-ID', '<company_logo>')
                inline_image.add_header('Content-Disposition', 'inline', filename=f'logo.{ext}')
                email.attachments.append(inline_image)

                logger.info(f"Logo attached inline to quote email")
            except Exception as logo_error:
                logger.warning(f"Failed to attach logo to email: {logo_error}")
                # Email will still be sent without logo

        # Send email
        email.send(fail_silently=False)
        logger.info(f"Quote {quote.quote_number} sent successfully to {recipient_email}")

        return {
            'success': True,
            'message': f'Quote sent successfully to {recipient_email}'
        }

    except Exception as e:
        logger.error(f"Failed to send quote {quote.quote_number} to {recipient_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def send_invoice_email(invoice, recipient_email=None):
    """
    Send invoice via email to client with PDF attachment

    Args:
        invoice: Invoice instance
        recipient_email: Optional email override, defaults to client email

    Returns:
        dict: Result with success/error message
    """
    # Use client email if not specified
    if not recipient_email:
        recipient_email = invoice.client.email

    if not recipient_email:
        return {
            'success': False,
            'error': 'No email address available for this client'
        }

    try:
        # Generate PDF
        pdf_data = generate_invoice_pdf(invoice)

        # Prepare email context
        context = {
            'invoice': invoice,
            'company': invoice.company,
            'client': invoice.client,
        }

        # Render email body
        subject = f'Invoice {invoice.invoice_number} from {invoice.company.name}'

        # Check if company has a logo for inline attachment
        has_logo = bool(invoice.company.logo)

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2563eb;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .company-logo {{
                    max-width: 150px;
                    max-height: 80px;
                    margin-bottom: 10px;
                }}
                .content {{
                    background-color: #f9fafb;
                    padding: 30px;
                    border: 1px solid #e5e7eb;
                }}
                .details {{
                    background-color: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                }}
                .details table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .details td {{
                    padding: 8px 0;
                }}
                .details td:first-child {{
                    font-weight: bold;
                    color: #6b7280;
                    width: 40%;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #2563eb;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin: 20px 0;
                }}
                .status-paid {{
                    color: #059669;
                    font-weight: bold;
                }}
                .status-due {{
                    color: #dc2626;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    {f'<img src="cid:company_logo" alt="{invoice.company.name}" class="company-logo" />' if has_logo else ''}
                    <h1>Invoice</h1>
                    <p>{invoice.invoice_number}</p>
                </div>

                <div class="content">
                    <p>Dear {invoice.client.name},</p>

                    <p>Please find attached invoice <strong>{invoice.invoice_number}</strong> for your records and payment.</p>

                    <div class="details">
                        <table>
                            <tr>
                                <td>Invoice Number:</td>
                                <td>{invoice.invoice_number}</td>
                            </tr>
                            <tr>
                                <td>Issue Date:</td>
                                <td>{invoice.issue_date.strftime('%B %d, %Y')}</td>
                            </tr>
                            <tr>
                                <td>Due Date:</td>
                                <td>{invoice.due_date.strftime('%B %d, %Y')}</td>
                            </tr>
                            <tr>
                                <td>Total Amount:</td>
                                <td><strong>{format_currency(invoice.total_amount, invoice.company.currency)}</strong></td>
                            </tr>
                            {f'''<tr>
                                <td>Amount Paid:</td>
                                <td class="status-paid">{format_currency(invoice.amount_paid, invoice.company.currency)}</td>
                            </tr>
                            <tr>
                                <td>Amount Due:</td>
                                <td class="status-due">{format_currency(invoice.amount_due, invoice.company.currency)}</td>
                            </tr>''' if invoice.amount_paid > 0 else ''}
                            <tr>
                                <td>Status:</td>
                                <td><strong>{invoice.get_status_display()}</strong></td>
                            </tr>
                        </table>
                    </div>

                    <p>The complete invoice details are attached as a PDF document. Payment is due by {invoice.due_date.strftime('%B %d, %Y')}.</p>

                    {f'<p><strong>Additional Notes:</strong><br/>{invoice.notes}</p>' if invoice.notes else ''}

                    <p>If you have any questions regarding this invoice, please don't hesitate to contact us.</p>

                    <p>Best regards,<br/>
                    <strong>{invoice.company.name}</strong><br/>
                    {getattr(invoice.company, 'email', '') or ''}</p>
                </div>

                <div class="footer">
                    <p>This is an automated email. Please do not reply directly to this message.</p>
                    <p>&copy; {invoice.company.name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_message = f"""
        Invoice {invoice.invoice_number}

        Dear {invoice.client.name},

        Please find attached invoice {invoice.invoice_number} for your records and payment.

        Invoice Details:
        - Invoice Number: {invoice.invoice_number}
        - Issue Date: {invoice.issue_date.strftime('%B %d, %Y')}
        - Due Date: {invoice.due_date.strftime('%B %d, %Y')}
        - Total Amount: {format_currency(invoice.total_amount, invoice.company.currency)}
        {f'- Amount Paid: {format_currency(invoice.amount_paid, invoice.company.currency)}' if invoice.amount_paid > 0 else ''}
        {f'- Amount Due: {format_currency(invoice.amount_due, invoice.company.currency)}' if invoice.amount_paid > 0 else ''}
        - Status: {invoice.get_status_display()}

        The complete invoice details are attached as a PDF document.

        {f'Additional Notes: {invoice.notes}' if invoice.notes else ''}

        Best regards,
        {invoice.company.name}
        {getattr(invoice.company, 'email', '') or ''}
        """

        # Create email
        company_email = getattr(invoice.company, 'email', None)
        email = EmailMessage(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
            reply_to=[company_email] if company_email else None,
        )

        # Attach PDF
        email.attach(
            f'Invoice-{invoice.invoice_number}.pdf',
            pdf_data,
            'application/pdf'
        )

        # Set HTML content
        email.content_subtype = 'html'
        email.body = html_message

        # Attach company logo as inline image if it exists
        if invoice.company.logo:
            try:
                # Download the logo from GCS
                logo_url = invoice.company.logo.url
                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                # Get the file extension
                logo_name = invoice.company.logo.name
                ext = logo_name.split('.')[-1] if '.' in logo_name else 'png'

                # Attach as inline image with Content-ID
                from email.mime.image import MIMEImage
                inline_image = MIMEImage(response.content)
                inline_image.add_header('Content-ID', '<company_logo>')
                inline_image.add_header('Content-Disposition', 'inline', filename=f'logo.{ext}')
                email.attachments.append(inline_image)

                logger.info(f"Logo attached inline to invoice email")
            except Exception as logo_error:
                logger.warning(f"Failed to attach logo to email: {logo_error}")
                # Email will still be sent without logo

        # Send email
        email.send(fail_silently=False)
        logger.info(f"Invoice {invoice.invoice_number} sent successfully to {recipient_email}")

        return {
            'success': True,
            'message': f'Invoice sent successfully to {recipient_email}'
        }

    except Exception as e:
        logger.error(f"Failed to send invoice {invoice.invoice_number} to {recipient_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
