# Generated migration for adding language field to Company model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0004_company_brand_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='language',
            field=models.CharField(default='en', help_text='The default language code (e.g., en, fr).', max_length=2),
        ),
    ]
