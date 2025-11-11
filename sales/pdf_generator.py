"""
PDF Generator for Quotes and Invoices
Generates professional PDF documents with company branding
"""
import os
import io
import qrcode
import requests
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from django.conf import settings
from .utils import format_currency, get_pdf_text


class QuotePDF:
    """Generate PDF for Quotes with company branding"""

    def __init__(self, quote, template='default'):
        self.quote = quote
        self.company = quote.company
        self.currency = quote.company.currency
        self.language = getattr(quote.company, 'language', 'en')
        self.buffer = io.BytesIO()
        self.pagesize = letter
        self.width, self.height = self.pagesize
        self.template = template  # 'default', 'modern', 'classic'

    def _get_logo_path(self):
        """Get the absolute path to company logo or download from GCS"""
        if self.company.logo:
            # Try to get local file path first
            try:
                logo_path = self.company.logo.path
                if os.path.exists(logo_path):
                    return logo_path
            except (ValueError, NotImplementedError, AttributeError):
                # Logo is stored in GCS, download it
                try:
                    logo_url = self.company.logo.url
                    response = requests.get(logo_url, timeout=10)
                    response.raise_for_status()
                    # Return BytesIO object instead of path
                    return io.BytesIO(response.content)
                except Exception as e:
                    print(f"Error downloading logo from GCS: {e}")
                    pass
        return None

    def _generate_qr_code(self):
        """Generate QR code for quote tracking"""
        # Create tracking URL
        tracking_url = f"{settings.FRONTEND_URL or 'https://app.progestock.com'}/quotes/view/{self.quote.id}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(tracking_url)
        qr.make(fit=True)

        # Create an image from the QR Code
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        return qr_buffer

    def _create_header(self, elements, styles):
        """Create PDF header with company logo, info, and QR code"""
        header_data = []

        # Left: Company logo
        logo_path = self._get_logo_path()
        if logo_path:
            try:
                logo = Image(logo_path, width=1.2*inch, height=1.2*inch, kind='proportional')
            except Exception as e:
                print(f"Error loading logo: {e}")
                logo = Paragraph(f'<b>{self.company.name}</b>', styles['Heading1'])
        else:
            logo = Paragraph(f'<b>{self.company.name}</b>', styles['Heading1'])

        # Middle: Company information
        company_info_text = f'''<b><font size="16">{self.company.name}</font></b><br/>'''

        # Add company details if available
        address = getattr(self.company, 'address', None)
        phone = getattr(self.company, 'phone', None)
        email = getattr(self.company, 'email', None)

        if address or phone or email:
            company_info_text += '<font size="9">'
            if address:
                company_info_text += f'{address}<br/>'
            if phone:
                company_info_text += f'{phone}<br/>'
            if email:
                company_info_text += f'{email}<br/>'
            company_info_text += '</font>'

        company_info = Paragraph(company_info_text, styles['Normal'])

        # Right: QR Code for tracking
        try:
            qr_buffer = self._generate_qr_code()
            qr_image = Image(qr_buffer, width=1*inch, height=1*inch)
            qr_cell = qr_image
        except Exception as e:
            print(f"Error generating QR code: {e}")
            qr_cell = ''

        header_data.append([logo, company_info, qr_cell])

        header_table = Table(header_data, colWidths=[1.5*inch, 4*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_title(self, elements, styles):
        """Create document title"""
        title_text = get_pdf_text('quotation', self.language)
        title = Paragraph(
            f'<b><font size="16">{title_text}</font></b>',
            ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                alignment=TA_CENTER,
                spaceAfter=12
            )
        )
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))

    def _create_info_section(self, elements, styles):
        """Create quote information section"""
        # Left side - Quote details
        left_info = [
            [Paragraph(f'<b>{get_pdf_text("quote_number", self.language)}</b>', styles['Normal']), Paragraph(self.quote.quote_number, styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("status", self.language)}</b>', styles['Normal']), Paragraph(self.quote.get_status_display(), styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("date_issued", self.language)}</b>', styles['Normal']), Paragraph(self.quote.date_issued.strftime('%B %d, %Y'), styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("valid_until", self.language)}</b>', styles['Normal']), Paragraph(self.quote.expiration_date.strftime('%B %d, %Y'), styles['Normal'])],
        ]

        # Right side - Client details
        right_info = [
            [Paragraph(f'<b>{get_pdf_text("bill_to", self.language)}</b>', styles['Normal']), Paragraph(self.quote.client.name, styles['Normal'])],
        ]

        if self.quote.client.email:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("email", self.language)}</b>', styles['Normal']),
                Paragraph(self.quote.client.email, styles['Normal'])
            ])
        if self.quote.client.phone:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("phone", self.language)}</b>', styles['Normal']),
                Paragraph(self.quote.client.phone, styles['Normal'])
            ])
        if self.quote.client.address:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("address", self.language)}</b>', styles['Normal']),
                Paragraph(self.quote.client.address, styles['Normal'])
            ])

        # Create tables
        left_table = Table(left_info, colWidths=[1.5*inch, 2*inch])
        left_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        right_table = Table(right_info, colWidths=[1.5*inch, 2*inch])
        right_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Combine into two columns
        info_table = Table([[left_table, right_table]], colWidths=[3.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_line_items_table(self, elements, styles):
        """Create table of line items"""
        # Table headers
        data = [[
            '#',
            get_pdf_text('product', self.language),
            get_pdf_text('sku', self.language),
            get_pdf_text('qty', self.language),
            get_pdf_text('unit_price', self.language),
            get_pdf_text('discount', self.language),
            get_pdf_text('total', self.language)
        ]]

        # Add line items
        for idx, item in enumerate(self.quote.line_items.all(), 1):
            discount_display = ''
            if item.discount_value > 0:
                if item.discount_type == 'PERCENTAGE':
                    discount_display = f'{item.discount_value}%'
                else:
                    discount_display = format_currency(item.discount_value, self.currency)
            else:
                discount_display = '-'

            data.append([
                str(idx),
                item.product_name,
                item.product_sku,
                str(item.quantity),
                format_currency(item.unit_price, self.currency),
                discount_display,
                format_currency(item.line_total, self.currency)
            ])

        # Create table
        table = Table(data, colWidths=[0.4*inch, 2.2*inch, 1*inch, 0.6*inch, 1*inch, 0.8*inch, 1*inch])

        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),

            # Body styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Index column
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),  # Qty column
            ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),  # Price columns
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_totals_section(self, elements, styles):
        """Create totals section"""
        # Create custom style for right-aligned text
        right_style = ParagraphStyle(
            'RightAlign',
            parent=styles['Normal'],
            alignment=TA_RIGHT
        )

        totals_data = [
            [Paragraph(f'<b>{get_pdf_text("subtotal", self.language)}</b>', styles['Normal']),
             Paragraph(format_currency(self.quote.subtotal, self.currency), right_style)],
        ]

        if self.quote.tax_amount > 0:
            tax_label = f'{get_pdf_text("tax", self.language)} ({self.quote.tax_rate:.1f}%):'
            totals_data.append([
                Paragraph(f'<b>{tax_label}</b>', styles['Normal']),
                Paragraph(format_currency(self.quote.tax_amount, self.currency), right_style)
            ])

        totals_data.append([
            Paragraph(f'<b><font size="12">{get_pdf_text("total_amount", self.language)}</font></b>', styles['Normal']),
            Paragraph(f'<b><font size="12">{format_currency(self.quote.total_amount, self.currency)}</font></b>', right_style)
        ])

        # Create totals table (right-aligned)
        totals_table = Table(totals_data, colWidths=[1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, -1), (-1, -1), 12),
        ]))

        # Right align the totals table
        wrapper_table = Table([[None, totals_table]], colWidths=[4*inch, 3*inch])
        wrapper_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(wrapper_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_notes_section(self, elements, styles):
        """Create notes and terms section"""
        if self.quote.notes:
            elements.append(Paragraph(f'<b>{get_pdf_text("notes", self.language)}</b>', styles['Heading3']))
            elements.append(Paragraph(self.quote.notes, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

        if self.quote.terms:
            elements.append(Paragraph(f'<b>{get_pdf_text("terms_and_conditions", self.language)}</b>', styles['Heading3']))
            elements.append(Paragraph(self.quote.terms, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

    def _create_footer(self, elements, styles):
        """Create footer"""
        elements.append(Spacer(1, 0.5*inch))
        footer_text = f'''
        <para align="center">
            <font size="8" color="gray">
                {get_pdf_text("generated_on", self.language)} {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
                {get_pdf_text("quote", self.language)} #{self.quote.quote_number}
            </font>
        </para>
        '''
        elements.append(Paragraph(footer_text, styles['Normal']))

    def generate(self):
        """Generate the PDF and return the buffer"""
        # Create the PDF document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.pagesize,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )

        # Container for elements
        elements = []

        # Get styles
        styles = getSampleStyleSheet()

        # Build document sections
        self._create_header(elements, styles)
        self._create_title(elements, styles)
        self._create_info_section(elements, styles)
        self._create_line_items_table(elements, styles)
        self._create_totals_section(elements, styles)
        self._create_notes_section(elements, styles)
        self._create_footer(elements, styles)

        # Build PDF
        doc.build(elements)

        # Get PDF data
        pdf_data = self.buffer.getvalue()
        self.buffer.close()

        return pdf_data


class InvoicePDF:
    """Generate PDF for Invoices with company branding"""

    def __init__(self, invoice, template='default'):
        self.invoice = invoice
        self.company = invoice.company
        self.currency = invoice.company.currency
        self.language = getattr(invoice.company, 'language', 'en')
        self.buffer = io.BytesIO()
        self.pagesize = letter
        self.width, self.height = self.pagesize
        self.template = template  # 'default', 'modern', 'classic'

    def _get_logo_path(self):
        """Get the absolute path to company logo or download from GCS"""
        if self.company.logo:
            # Try to get local file path first
            try:
                logo_path = self.company.logo.path
                if os.path.exists(logo_path):
                    return logo_path
            except (ValueError, NotImplementedError, AttributeError):
                # Logo is stored in GCS, download it
                try:
                    logo_url = self.company.logo.url
                    response = requests.get(logo_url, timeout=10)
                    response.raise_for_status()
                    # Return BytesIO object instead of path
                    return io.BytesIO(response.content)
                except Exception as e:
                    print(f"Error downloading logo from GCS: {e}")
                    pass
        return None

    def _generate_qr_code(self):
        """Generate QR code for invoice tracking"""
        # Create tracking URL
        tracking_url = f"{settings.FRONTEND_URL or 'https://app.progestock.com'}/invoices/view/{self.invoice.id}"

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(tracking_url)
        qr.make(fit=True)

        # Create an image from the QR Code
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        return qr_buffer

    def _create_header(self, elements, styles):
        """Create PDF header with company logo, info, and QR code"""
        header_data = []

        # Left: Company logo
        logo_path = self._get_logo_path()
        if logo_path:
            try:
                logo = Image(logo_path, width=1.2*inch, height=1.2*inch, kind='proportional')
            except Exception as e:
                print(f"Error loading logo: {e}")
                logo = Paragraph(f'<b>{self.company.name}</b>', styles['Heading1'])
        else:
            logo = Paragraph(f'<b>{self.company.name}</b>', styles['Heading1'])

        # Middle: Company information
        company_info_text = f'''<b><font size="16">{self.company.name}</font></b><br/>'''

        # Add company details if available
        address = getattr(self.company, 'address', None)
        phone = getattr(self.company, 'phone', None)
        email = getattr(self.company, 'email', None)

        if address or phone or email:
            company_info_text += '<font size="9">'
            if address:
                company_info_text += f'{address}<br/>'
            if phone:
                company_info_text += f'{phone}<br/>'
            if email:
                company_info_text += f'{email}<br/>'
            company_info_text += '</font>'

        company_info = Paragraph(company_info_text, styles['Normal'])

        # Right: QR Code for tracking
        try:
            qr_buffer = self._generate_qr_code()
            qr_image = Image(qr_buffer, width=1*inch, height=1*inch)
            qr_cell = qr_image
        except Exception as e:
            print(f"Error generating QR code: {e}")
            qr_cell = ''

        header_data.append([logo, company_info, qr_cell])

        header_table = Table(header_data, colWidths=[1.5*inch, 4*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_title(self, elements, styles):
        """Create document title"""
        title_text = get_pdf_text('invoice', self.language).upper()
        title = Paragraph(
            f'<b><font size="16">{title_text}</font></b>',
            ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                alignment=TA_CENTER,
                spaceAfter=12
            )
        )
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))

    def _create_info_section(self, elements, styles):
        """Create invoice information section"""
        # Left side - Invoice details
        left_info = [
            [Paragraph(f'<b>{get_pdf_text("invoice_number", self.language)}</b>', styles['Normal']), Paragraph(self.invoice.invoice_number, styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("status", self.language)}</b>', styles['Normal']), Paragraph(self.invoice.get_status_display(), styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("issue_date", self.language)}</b>', styles['Normal']), Paragraph(self.invoice.issue_date.strftime('%B %d, %Y'), styles['Normal'])],
            [Paragraph(f'<b>{get_pdf_text("due_date", self.language)}</b>', styles['Normal']), Paragraph(self.invoice.due_date.strftime('%B %d, %Y'), styles['Normal'])],
        ]

        if self.invoice.paid_date:
            left_info.append([
                Paragraph(f'<b>{get_pdf_text("paid_date", self.language)}</b>', styles['Normal']),
                Paragraph(self.invoice.paid_date.strftime('%B %d, %Y'), styles['Normal'])
            ])

        # Right side - Client details
        right_info = [
            [Paragraph(f'<b>{get_pdf_text("bill_to", self.language)}</b>', styles['Normal']), Paragraph(self.invoice.client.name, styles['Normal'])],
        ]

        if self.invoice.client.email:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("email", self.language)}</b>', styles['Normal']),
                Paragraph(self.invoice.client.email, styles['Normal'])
            ])
        if self.invoice.client.phone:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("phone", self.language)}</b>', styles['Normal']),
                Paragraph(self.invoice.client.phone, styles['Normal'])
            ])
        if self.invoice.client.address:
            right_info.append([
                Paragraph(f'<b>{get_pdf_text("address", self.language)}</b>', styles['Normal']),
                Paragraph(self.invoice.client.address, styles['Normal'])
            ])

        # Create tables
        left_table = Table(left_info, colWidths=[1.5*inch, 2*inch])
        left_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        right_table = Table(right_info, colWidths=[1.5*inch, 2*inch])
        right_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Combine into two columns
        info_table = Table([[left_table, right_table]], colWidths=[3.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_line_items_table(self, elements, styles):
        """Create table of line items"""
        # Table headers
        data = [[
            '#',
            get_pdf_text('product', self.language),
            get_pdf_text('sku', self.language),
            get_pdf_text('qty', self.language),
            get_pdf_text('unit_price', self.language),
            get_pdf_text('discount', self.language),
            get_pdf_text('total', self.language)
        ]]

        # Add line items
        for idx, item in enumerate(self.invoice.line_items.all(), 1):
            discount_display = ''
            if item.discount_value > 0:
                if item.discount_type == 'PERCENTAGE':
                    discount_display = f'{item.discount_value}%'
                else:
                    discount_display = format_currency(item.discount_value, self.currency)
            else:
                discount_display = '-'

            data.append([
                str(idx),
                item.product_name,
                item.product_sku,
                str(item.quantity),
                format_currency(item.unit_price, self.currency),
                discount_display,
                format_currency(item.line_total, self.currency)
            ])

        # Create table
        table = Table(data, colWidths=[0.4*inch, 2.2*inch, 1*inch, 0.6*inch, 1*inch, 0.8*inch, 1*inch])

        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),

            # Body styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Index column
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),  # Qty column
            ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),  # Price columns
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_totals_section(self, elements, styles):
        """Create totals section"""
        # Create custom style for right-aligned text
        right_style = ParagraphStyle(
            'RightAlign',
            parent=styles['Normal'],
            alignment=TA_RIGHT
        )

        totals_data = [
            [Paragraph(f'<b>{get_pdf_text("subtotal", self.language)}</b>', styles['Normal']),
             Paragraph(format_currency(self.invoice.subtotal, self.currency), right_style)],
        ]

        if self.invoice.tax_amount > 0:
            tax_label = f'{get_pdf_text("tax", self.language)} ({self.invoice.tax_rate:.1f}%):'
            totals_data.append([
                Paragraph(f'<b>{tax_label}</b>', styles['Normal']),
                Paragraph(format_currency(self.invoice.tax_amount, self.currency), right_style)
            ])

        totals_data.append([
            Paragraph(f'<b><font size="12">{get_pdf_text("total_amount", self.language)}</font></b>', styles['Normal']),
            Paragraph(f'<b><font size="12">{format_currency(self.invoice.total_amount, self.currency)}</font></b>', right_style)
        ])

        # Add payment info if partially paid or paid
        if self.invoice.amount_paid > 0:
            totals_data.append([
                Paragraph(f'<b>{get_pdf_text("amount_paid", self.language)}</b>', styles['Normal']),
                Paragraph(format_currency(self.invoice.amount_paid, self.currency), right_style)
            ])
            totals_data.append([
                Paragraph(f'<b><font size="12" color="red">{get_pdf_text("amount_due", self.language)}</font></b>', styles['Normal']),
                Paragraph(f'<b><font size="12" color="red">{format_currency(self.invoice.amount_due, self.currency)}</font></b>', right_style)
            ])

        # Create totals table (right-aligned)
        totals_table = Table(totals_data, colWidths=[1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, -1), (-1, -1), 12),
        ]))

        # Right align the totals table
        wrapper_table = Table([[None, totals_table]], colWidths=[4*inch, 3*inch])
        wrapper_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(wrapper_table)
        elements.append(Spacer(1, 0.3*inch))

    def _create_notes_section(self, elements, styles):
        """Create notes and terms section"""
        if self.invoice.notes:
            elements.append(Paragraph(f'<b>{get_pdf_text("notes", self.language)}</b>', styles['Heading3']))
            elements.append(Paragraph(self.invoice.notes, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

        if self.invoice.terms:
            elements.append(Paragraph(f'<b>{get_pdf_text("terms_and_conditions", self.language)}</b>', styles['Heading3']))
            elements.append(Paragraph(self.invoice.terms, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

    def _create_footer(self, elements, styles):
        """Create footer"""
        elements.append(Spacer(1, 0.5*inch))
        footer_text = f'''
        <para align="center">
            <font size="8" color="gray">
                {get_pdf_text("generated_on", self.language)} {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
                {get_pdf_text("invoice", self.language)} #{self.invoice.invoice_number}
            </font>
        </para>
        '''
        elements.append(Paragraph(footer_text, styles['Normal']))

    def generate(self):
        """Generate the PDF and return the buffer"""
        # Create the PDF document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.pagesize,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )

        # Container for elements
        elements = []

        # Get styles
        styles = getSampleStyleSheet()

        # Build document sections
        self._create_header(elements, styles)
        self._create_title(elements, styles)
        self._create_info_section(elements, styles)
        self._create_line_items_table(elements, styles)
        self._create_totals_section(elements, styles)
        self._create_notes_section(elements, styles)
        self._create_footer(elements, styles)

        # Build PDF
        doc.build(elements)

        # Get PDF data
        pdf_data = self.buffer.getvalue()
        self.buffer.close()

        return pdf_data


def generate_quote_pdf(quote, template='default'):
    """
    Convenience function to generate PDF for a quote

    Args:
        quote: Quote instance
        template: PDF template style ('default', 'modern', 'classic')

    Returns:
        bytes: PDF file content
    """
    generator = QuotePDF(quote, template=template)
    return generator.generate()


def generate_invoice_pdf(invoice, template='default'):
    """
    Convenience function to generate PDF for an invoice

    Args:
        invoice: Invoice instance
        template: PDF template style ('default', 'modern', 'classic')

    Returns:
        bytes: PDF file content
    """
    generator = InvoicePDF(invoice, template=template)
    return generator.generate()
