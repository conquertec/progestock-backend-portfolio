import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progestock_backend.settings')

app = Celery('progestock_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Explicitly import tasks to ensure they're registered
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Import tasks explicitly to ensure they're registered
    import inventory.tasks
