
import os
from django.conf import settings
from celery      import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskrunner.settings')

judge_app = Celery(
    "judge",
    backend = settings.CELERY_BACKEND,
    broker  = settings.CELERY_BROKER
)

judge_app.config_from_object('django.conf:settings', namespace='CELERY')
judge_app.autodiscover_tasks()