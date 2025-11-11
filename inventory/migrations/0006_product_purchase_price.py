# Generated migration for adding purchase_price field to Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_product_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='purchase_price',
            field=models.DecimalField(decimal_places=2, default=0.0, help_text='The cost/purchase price of the product for profit calculations.', max_digits=10),
        ),
    ]
