
from django.db import models
from django.contrib.auth.models import User

from problems.models.problem import Problem

class Clarification (models.Model):
    contest = models.ForeignKey("ccs.Contest", on_delete=models.PROTECT)
    author  = models.ForeignKey(User, on_delete=models.PROTECT, related_name="clr_author")
    team    = models.ForeignKey(User, on_delete=models.PROTECT, related_name="clr_original_team")

    reply_to = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        default=None,
        related_name="replies"
    )
    problem = models.ForeignKey(Problem, on_delete = models.PROTECT, null = True)

    content = models.TextField()
    time    = models.DateTimeField()
    broadcast = models.BooleanField()
