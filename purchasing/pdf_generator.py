"""
PDF Generator for Purchase Orders
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
from sales.utils import format_currency


class PurchaseOrderPDF:
    """Generate PDF for Purchase Orders with company branding"""

    def __init__(self, purchase_order, template='default'):
        self.po = purchase_order
        self.company = purchase_order.company
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
        """Generate QR code for PO tracking"""
        # Create tracking URL (you can customize this based on your domain)
        tracking_url = f"{settings.FRONTEND_URL or 'https://app.progestock.com'}/purchase-orders/{self.po.id}"

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

        # Add company details if available (using getattr for optional fields)
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
        title = Paragraph(
            '<b><font size="16">PURCHASE ORDER</font></b>',
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
        """Create PO information section"""
        # Left side - PO details
        left_info = [
            [Paragraph('<b>PO Number:</b>', styles['Normal']), Paragraph(self.po.po_number, styles['Normal'])],
            [Paragraph('<b>Status:</b>', styles['Normal']), Paragraph(self.po.get_status_display(), styles['Normal'])],
            [Paragraph('<b>Order Date:</b>', styles['Normal']), Paragraph(self.po.order_date.strftime('%B %d, %Y'), styles['Normal'])],
        ]

        if self.po.expected_delivery_date:
            left_info.append([
                Paragraph('<b>Expected Delivery:</b>', styles['Normal']),
                Paragraph(self.po.expected_delivery_date.strftime('%B %d, %Y'), styles['Normal'])
            ])

        # Right side - Supplier details
        right_info = [
            [Paragraph('<b>Supplier:</b>', styles['Normal']), Paragraph(self.po.supplier.name, styles['Normal'])],
        ]

        if self.po.supplier.contact_person:
            right_info.append([
                Paragraph('<b>Contact Person:</b>', styles['Normal']),
                Paragraph(self.po.supplier.contact_person, styles['Normal'])
            ])
        if self.po.supplier.email:
            right_info.append([
                Paragraph('<b>Email:</b>', styles['Normal']),
                Paragraph(self.po.supplier.email, styles['Normal'])
            ])
        if self.po.supplier.phone:
            right_info.append([
                Paragraph('<b>Phone:</b>', styles['Normal']),
                Paragraph(self.po.supplier.phone, styles['Normal'])
            ])
        if self.po.supplier.address:
            right_info.append([
                Paragraph('<b>Address:</b>', styles['Normal']),
                Paragraph(self.po.supplier.address, styles['Normal'])
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
        data = [['#', 'Product', 'SKU', 'Qty', 'Unit Price', 'Discount', 'Total']]

        # Add line items
        for idx, item in enumerate(self.po.line_items.all(), 1):
            discount_display = ''
            if item.discount_value > 0:
                if item.discount_type == 'PERCENTAGE':
                    discount_display = f'{item.discount_value}%'
                else:
                    discount_display = format_currency(item.discount_value, self.company.currency)
            else:
                discount_display = '-'

            data.append([
                str(idx),
                item.product_name,
                item.product_sku,
                str(item.quantity_ordered),
                format_currency(item.unit_price, self.company.currency),
                discount_display,
                format_currency(item.line_total, self.company.currency)
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
            [Paragraph('<b>Subtotal:</b>', styles['Normal']), Paragraph(format_currency(self.po.subtotal, self.company.currency), right_style)],
        ]

        if self.po.tax_amount > 0:
            totals_data.append([
                Paragraph('<b>Tax ({:.1f}%):</b>'.format(self.po.tax_rate), styles['Normal']),
                Paragraph(format_currency(self.po.tax_amount, self.company.currency), right_style)
            ])

        if self.po.shipping_cost > 0:
            totals_data.append([
                Paragraph('<b>Shipping:</b>', styles['Normal']),
                Paragraph(format_currency(self.po.shipping_cost, self.company.currency), right_style)
            ])

        totals_data.append([
            Paragraph('<b><font size="12">Total Amount:</font></b>', styles['Normal']),
            Paragraph(f'<b><font size="12">{format_currency(self.po.total_amount, self.company.currency)}</font></b>', right_style)
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
        if self.po.notes:
            elements.append(Paragraph('<b>Notes:</b>', styles['Heading3']))
            elements.append(Paragraph(self.po.notes, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

        if self.po.terms:
            elements.append(Paragraph('<b>Terms and Conditions:</b>', styles['Heading3']))
            elements.append(Paragraph(self.po.terms, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))

        # Receiving location
        elements.append(Paragraph(f'<b>Receiving Location:</b> {self.po.receiving_location.name}', styles['Normal']))

    def _create_footer(self, elements, styles):
        """Create footer"""
        elements.append(Spacer(1, 0.5*inch))
        footer_text = f'''
        <para align="center">
            <font size="8" color="gray">
                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
                Purchase Order #{self.po.po_number}
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


def generate_purchase_order_pdf(purchase_order, template='default'):
    """
    Convenience function to generate PDF for a purchase order

    Args:
        purchase_order: PurchaseOrder instance
        template: PDF template style ('default', 'modern', 'classic')

    Returns:
        bytes: PDF file content
    """
    generator = PurchaseOrderPDF(purchase_order, template=template)
    return generator.generate()
