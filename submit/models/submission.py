
from django.db import models
from django.contrib.auth.models import User
from django_enumfield import enum

from submit.models.status import SubmissionStatus
from submit.models.verdict import SubmissionVerdict

from django.db import transaction

class Submission (models.Model):
    user = models.ForeignKey(User, on_delete = models.PROTECT)

    status  = enum.EnumField(SubmissionStatus,  default = SubmissionStatus.STARTING)
    verdict = enum.EnumField(SubmissionVerdict, default = SubmissionVerdict.PENDING)

    code_location = models.TextField()
    exec_location = models.TextField()

    @staticmethod
    def set_submission_information (
        submission_pk : int,
        status  : "SubmissionStatus  | None" = None,
        verdict : "SubmissionVerdict | None" = None):
        with transaction.atomic():
            updates = {}
            if status  is not None: updates['status']  = status
            if verdict is not None: updates['verdict'] = verdict

            rows_updated = Submission.objects \
                .filter(pk = submission_pk) \
                .update(**updates)
            
            if rows_updated == 0:
                raise Submission.DoesNotExist(
                    f"Could not set submission information for pk={submission_pk}")
            
        # TODO notify channel of change
