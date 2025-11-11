"""
Email service for sending purchase orders to suppliers
"""
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .pdf_generator import generate_purchase_order_pdf
from sales.utils import format_currency
import logging
import requests
from io import BytesIO

logger = logging.getLogger(__name__)


def send_purchase_order_email(purchase_order, recipient_email=None):
    """
    Send purchase order via email to supplier with PDF attachment

    Args:
        purchase_order: PurchaseOrder instance
        recipient_email: Optional email override, defaults to supplier email

    Returns:
        dict: Result with success/error message
    """
    # Use supplier email if not specified
    if not recipient_email:
        recipient_email = purchase_order.supplier.email

    if not recipient_email:
        return {
            'success': False,
            'error': 'No email address available for this supplier'
        }

    try:
        # Generate PDF
        pdf_data = generate_purchase_order_pdf(purchase_order)

        # Prepare email context
        context = {
            'po': purchase_order,
            'company': purchase_order.company,
            'supplier': purchase_order.supplier,
        }

        # Render email body
        subject = f'Purchase Order {purchase_order.po_number} from {purchase_order.company.name}'

        # Check if company has a logo for inline attachment
        has_logo = bool(purchase_order.company.logo)

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
                    {f'<img src="cid:company_logo" alt="{purchase_order.company.name}" class="company-logo" />' if has_logo else ''}
                    <h1>Purchase Order</h1>
                    <p>{purchase_order.po_number}</p>
                </div>

                <div class="content">
                    <p>Dear {purchase_order.supplier.contact_person or 'Supplier'},</p>

                    <p>Please find attached our purchase order <strong>{purchase_order.po_number}</strong> for your review and processing.</p>

                    <div class="details">
                        <table>
                            <tr>
                                <td>PO Number:</td>
                                <td>{purchase_order.po_number}</td>
                            </tr>
                            <tr>
                                <td>Order Date:</td>
                                <td>{purchase_order.order_date.strftime('%B %d, %Y')}</td>
                            </tr>
                            {f'''<tr>
                                <td>Expected Delivery:</td>
                                <td>{purchase_order.expected_delivery_date.strftime('%B %d, %Y')}</td>
                            </tr>''' if purchase_order.expected_delivery_date else ''}
                            <tr>
                                <td>Total Amount:</td>
                                <td><strong>{format_currency(purchase_order.total_amount, purchase_order.company.currency)}</strong></td>
                            </tr>
                            <tr>
                                <td>Receiving Location:</td>
                                <td>{purchase_order.receiving_location.name}</td>
                            </tr>
                        </table>
                    </div>

                    <p>The complete purchase order details are attached as a PDF document. Please review and confirm receipt of this order.</p>

                    {f'<p><strong>Additional Notes:</strong><br/>{purchase_order.notes}</p>' if purchase_order.notes else ''}

                    <p>If you have any questions or concerns, please don't hesitate to contact us.</p>

                    <p>Best regards,<br/>
                    <strong>{purchase_order.company.name}</strong><br/>
                    {getattr(purchase_order.company, 'email', '') or ''}</p>
                </div>

                <div class="footer">
                    <p>This is an automated email. Please do not reply directly to this message.</p>
                    <p>&copy; {purchase_order.company.name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_message = f"""
        Purchase Order {purchase_order.po_number}

        Dear {purchase_order.supplier.contact_person or 'Supplier'},

        Please find attached our purchase order {purchase_order.po_number} for your review and processing.

        Order Details:
        - PO Number: {purchase_order.po_number}
        - Order Date: {purchase_order.order_date.strftime('%B %d, %Y')}
        {f'- Expected Delivery: {purchase_order.expected_delivery_date.strftime("%B %d, %Y")}' if purchase_order.expected_delivery_date else ''}
        - Total Amount: {format_currency(purchase_order.total_amount, purchase_order.company.currency)}
        - Receiving Location: {purchase_order.receiving_location.name}

        The complete purchase order details are attached as a PDF document.

        {f'Additional Notes: {purchase_order.notes}' if purchase_order.notes else ''}

        Best regards,
        {purchase_order.company.name}
        {getattr(purchase_order.company, 'email', '') or ''}
        """

        # Create email
        company_email = getattr(purchase_order.company, 'email', None)
        email = EmailMessage(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
            reply_to=[company_email] if company_email else None,
        )

        # Attach PDF
        email.attach(
            f'PO-{purchase_order.po_number}.pdf',
            pdf_data,
            'application/pdf'
        )

        # Set HTML content
        email.content_subtype = 'html'
        email.body = html_message

        # Attach company logo as inline image if it exists
        if purchase_order.company.logo:
            try:
                # Download the logo from GCS
                logo_url = purchase_order.company.logo.url
                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                # Get the file extension
                logo_name = purchase_order.company.logo.name
                ext = logo_name.split('.')[-1] if '.' in logo_name else 'png'

                # Attach as inline image with Content-ID
                email.attach(f'logo.{ext}', response.content, f'image/{ext}')
                # Set the Content-ID for the attachment
                email.attachments[-1] = (email.attachments[-1][0], email.attachments[-1][1], email.attachments[-1][2])
                # Mark it as inline
                from email.mime.image import MIMEImage
                inline_image = MIMEImage(response.content)
                inline_image.add_header('Content-ID', '<company_logo>')
                inline_image.add_header('Content-Disposition', 'inline', filename=f'logo.{ext}')
                # Replace the last attachment with our inline image
                email.attachments[-1] = inline_image

                logger.info(f"Logo attached inline to purchase order email")
            except Exception as logo_error:
                logger.warning(f"Failed to attach logo to email: {logo_error}")
                # Email will still be sent without logo

        # Send email
        email.send(fail_silently=False)
        logger.info(f"Purchase order {purchase_order.po_number} sent successfully to {recipient_email}")

        return {
            'success': True,
            'message': f'Purchase order sent successfully to {recipient_email}'
        }

    except Exception as e:
        logger.error(f"Failed to send purchase order {purchase_order.po_number} to {recipient_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
