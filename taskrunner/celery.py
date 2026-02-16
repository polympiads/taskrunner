
from multiprocessing import current_process
import os
from django.conf import settings
from celery      import Celery
from celery.signals import worker_process_init

from taskrunner.telemetry import init_telemetry

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskrunner.settings')

judge_app = Celery(
    "judge",
    backend = settings.CELERY_BACKEND,
    broker  = settings.CELERY_BROKER
)

judge_app.config_from_object('django.conf:settings', namespace='CELERY')
judge_app.autodiscover_tasks()

@worker_process_init.connect
def setup_worker (**kwargs):
    init_telemetry()

    process_name = current_process().name
    try:
        process_id = int(process_name.split("-")[-1])
        from sandbox.manager import SandboxManager

        SandboxManager.instance().setup_worker(process_id)
    except Exception as err:
        print("Invalid process name, should be of the form 'Something-<UUID>'")
        raise err
