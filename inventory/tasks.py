from celery import shared_task
import csv
from io import StringIO
from .models import Product, Category, Company

@shared_task
def process_product_import(csv_content, company_id):
    """
    A Celery task to process a CSV file and bulk import products.
    """
    try:
        company = Company.objects.get(id=company_id)
        # Use StringIO to treat the string content as a file
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        products_to_create = []
        errors = []
        
        for row_num, row in enumerate(reader, start=2): # Start at row 2 for error reporting
            name = row.get('name')
            sku = row.get('sku', '')
            price = row.get('price', 0.00)
            category_name = row.get('category', '')
            
            if not name:
                errors.append(f"Row {row_num}: 'name' is a required field.")
                continue

            # Find or create the category
            category = None
            if category_name:
                category, _ = Category.objects.get_or_create(
                    name=category_name, 
                    company=company
                )

            products_to_create.append(
                Product(
                    company=company,
                    name=name,
                    sku=sku,
                    price=price,
                    category=category
                )
            )

        # Use bulk_create for high efficiency
        if products_to_create:
            Product.objects.bulk_create(products_to_create)
            
        # You can add more sophisticated reporting here, like sending an email.
        # For now, we'll log the result.
        result_message = f"Import for company {company.name} complete. {len(products_to_create)} products created. {len(errors)} errors found."
        print(result_message)
        if errors:
            print("Errors:", errors)
            
        return result_message

    except Exception as e:
        print(f"An unexpected error occurred during product import: {str(e)}")
        return f"Import failed: {str(e)}"
