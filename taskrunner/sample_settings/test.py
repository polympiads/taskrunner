
from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        "TEST": {
            "NAME": os.path.join(BASE_DIR, "db_test.sqlite3"),
        },
    },
}

STORAGE_CLIENT  = BaseStorageClient()

CELERY_BACKEND = "redis://localhost:6379/0"
CELERY_BROKER  = "pyamqp://guest@localhost//"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
