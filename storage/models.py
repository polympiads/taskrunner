
from django.db import models

import uuid6

class StorageEntry (models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid6.uuid7,
        editable=False
    )
    extension = models.CharField(max_length=10)
