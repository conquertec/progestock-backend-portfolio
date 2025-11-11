from django.db.models.signals import post_save
from django.dispatch import receiver
from company.models import Company  # The model we are listening to
from .models import LogEntry       # The log model we are creating

# @receiver(post_save, sender=Company)
# def log_company_creation(sender, instance, created, **kwargs):
#     """
#     A signal receiver that runs every time a Company object is saved.
#     It creates a log entry only if the company is newly created.
#     """
#     # The 'created' flag is True only on the first save (i.e., creation).
#     if created:
#         # The user who triggered this is the first user of the company.
#         user = instance.users.first()
        
#         LogEntry.objects.create(
#             user=user,
#             company=instance,
#             action_type='COMPANY_CREATED',
#             details={
#                 'company_id': instance.id,
#                 'company_name': instance.name,
#                 'industry': instance.industry,
#             }
#         )
#         print(f"AUDIT LOG: Company '{instance.name}' created by user '{user.email}'.")