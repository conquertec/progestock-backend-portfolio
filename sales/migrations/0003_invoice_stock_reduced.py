# Generated migration for adding stock_reduced field to Invoice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_invoice_invoicelineitem_payment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='stock_reduced',
            field=models.BooleanField(default=False, help_text='Whether stock has been reduced for this invoice'),
        ),
    ]
