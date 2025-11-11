"""
Utility functions for sales module
"""

# Currency symbols mapping
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'CAD': 'CA$',
    'GHS': 'GH₵',
    'XAF': 'FCFA',
    'XOF': 'CFA',
    'NGN': '₦',
    'CFA': 'FCFA',
}

# Text translations for PDF documents
PDF_TRANSLATIONS = {
    'en': {
        'quotation': 'QUOTATION',
        'invoice': 'INVOICE',
        'purchase_order': 'PURCHASE ORDER',
        'quote_number': 'Quote Number:',
        'invoice_number': 'Invoice Number:',
        'po_number': 'PO Number:',
        'status': 'Status:',
        'date_issued': 'Date Issued:',
        'valid_until': 'Valid Until:',
        'issue_date': 'Issue Date:',
        'due_date': 'Due Date:',
        'paid_date': 'Paid Date:',
        'order_date': 'Order Date:',
        'expected_delivery': 'Expected Delivery:',
        'bill_to': 'Bill To:',
        'supplier': 'Supplier:',
        'email': 'Email:',
        'phone': 'Phone:',
        'address': 'Address:',
        'contact_person': 'Contact Person:',
        'product': 'Product',
        'sku': 'SKU',
        'qty': 'Qty',
        'unit_price': 'Unit Price',
        'discount': 'Discount',
        'total': 'Total',
        'subtotal': 'Subtotal:',
        'tax': 'Tax',
        'shipping': 'Shipping:',
        'total_amount': 'Total Amount:',
        'amount_paid': 'Amount Paid:',
        'amount_due': 'Amount Due:',
        'notes': 'Notes:',
        'terms_and_conditions': 'Terms and Conditions:',
        'receiving_location': 'Receiving Location:',
        'generated_on': 'Generated on',
        'quote': 'Quote',
        'invoice': 'Invoice',
    },
    'fr': {
        'quotation': 'DEVIS',
        'invoice': 'FACTURE',
        'purchase_order': 'BON DE COMMANDE',
        'quote_number': 'Numéro de devis :',
        'invoice_number': 'Numéro de facture :',
        'po_number': 'N° de commande :',
        'status': 'Statut :',
        'date_issued': 'Date d\'émission :',
        'valid_until': 'Valide jusqu\'au :',
        'issue_date': 'Date d\'émission :',
        'due_date': 'Date d\'échéance :',
        'paid_date': 'Date de paiement :',
        'order_date': 'Date de commande :',
        'expected_delivery': 'Livraison prévue :',
        'bill_to': 'Facturer à :',
        'supplier': 'Fournisseur :',
        'email': 'Email :',
        'phone': 'Téléphone :',
        'address': 'Adresse :',
        'contact_person': 'Personne de contact :',
        'product': 'Produit',
        'sku': 'SKU',
        'qty': 'Qté',
        'unit_price': 'Prix unitaire',
        'discount': 'Remise',
        'total': 'Total',
        'subtotal': 'Sous-total :',
        'tax': 'Taxe',
        'shipping': 'Livraison :',
        'total_amount': 'Montant total :',
        'amount_paid': 'Montant payé :',
        'amount_due': 'Montant dû :',
        'notes': 'Notes :',
        'terms_and_conditions': 'Termes et conditions :',
        'receiving_location': 'Lieu de réception :',
        'generated_on': 'Généré le',
        'quote': 'Devis',
        'invoice': 'Facture',
    }
}


def get_currency_symbol(currency_code):
    """
    Get the currency symbol for a given currency code.

    Args:
        currency_code (str): Currency code (e.g., 'USD', 'EUR')

    Returns:
        str: Currency symbol
    """
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)


def format_currency(amount, currency_code):
    """
    Format a monetary amount with the appropriate currency symbol.

    Args:
        amount (Decimal/float): The amount to format
        currency_code (str): Currency code (e.g., 'USD', 'EUR')

    Returns:
        str: Formatted currency string
    """
    symbol = get_currency_symbol(currency_code)

    # For currencies that go after the amount
    if currency_code in ['XAF', 'XOF', 'CFA']:
        return f'{amount:.2f} {symbol}'

    # Default: symbol before amount
    return f'{symbol}{amount:.2f}'


def get_pdf_text(key, language='en'):
    """
    Get translated text for PDF documents.

    Args:
        key (str): Translation key
        language (str): Language code ('en' or 'fr')

    Returns:
        str: Translated text
    """
    lang = language.lower() if language else 'en'
    if lang not in PDF_TRANSLATIONS:
        lang = 'en'

    return PDF_TRANSLATIONS[lang].get(key, key)
