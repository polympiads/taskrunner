
"""
CCS Event Feed Permanent Storage

The pipeline is the following :
- When a new event is created,
it is first pre registered in the 
EventFeedPreRegistration
- Using the pk from the pre
registration, we fill the "token"
field of the json event feed.
"""

import json
import channels.layers
from typing import Any, Literal, TypedDict

from django.db import models
from django.contrib.auth.models import User
from django_enumfield import enum

from ccs.models.contest import Contest
from ccs.models.visible import Visibility

class EventFeed (models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.PROTECT)
    owner   = models.ForeignKey(User, null=True, on_delete=models.PROTECT)

    visibility  = enum.EnumField(Visibility)
    raw_payload = models.TextField()

    @property
    def full_payload (self):
        payload: str = ('{"token":"' + str(self.pk) + '",' + self.raw_payload[1:] + "\n")
        return payload.encode()
