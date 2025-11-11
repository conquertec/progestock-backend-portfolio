# Generated migration for adding profile_picture field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_user_last_active_user_role_invitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_picture',
            field=models.URLField(blank=True, help_text="URL to user's profile picture (e.g., from Google)", max_length=500, null=True),
        ),
    ]
