
from celery import chain
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django_enumfield import enum

from judge.languages import LanguageKind, get_language
from problems.models.problem import Problem
from submit.models.status import SubmissionStatus
from submit.models.verdict import SubmissionVerdict

from django.db import transaction

class SubmissionManager (models.Manager):
    def create_submission (
        self,
        user    : User,
        problem : Problem,

        code_location : str,

        language_kind : LanguageKind
    ):
        with transaction.atomic():
            language = get_language(language_kind)

            exec_location = settings.STORAGE_CLIENT.reserve()

            submission = Submission.objects.create(
                user    = user,
                problem = problem,

                code_location = code_location,
                exec_location = exec_location,

                language = language_kind
            )

            from judge.tasks.icpc.compile   import compile_task
            from judge.tasks.icpc.scheduler import scheduler_task

            from judge.tasks.icpc.compile import CompilationInput, CompilationResult
            from judge.tasks.icpc.subinfo import SubmissionInformation

            signature = chain(
                compile_task.s( CompilationInput(
                    submission.id,
                    code_location,
                    exec_location,
                    language_kind,
                    1.,
                    1.
                ).serialize() ),
                scheduler_task.s(
                    SubmissionInformation(
                        submission.pk,
                        problem.problem_location,
                        exec_location,
                        language_kind
                    ).serialize()
                )
            )
            transaction.on_commit(lambda : signature.apply_async())

            return submission

class Submission (models.Model):
    user = models.ForeignKey(User, on_delete = models.PROTECT)
    problem = models.ForeignKey(Problem, on_delete = models.PROTECT)

    status  = enum.EnumField(SubmissionStatus,  default = SubmissionStatus.STARTING)
    verdict = enum.EnumField(SubmissionVerdict, default = SubmissionVerdict.PENDING)

    language = enum.EnumField(LanguageKind)

    code_location = models.TextField()
    exec_location = models.TextField()

    first_wrong_test = models.IntegerField( default = -1 )

    objects : "models.Manager[Submission] | SubmissionManager" = SubmissionManager()

    @staticmethod
    def set_submission_information (
        submission_pk : int,
        status  : "SubmissionStatus  | None" = None,
        verdict : "SubmissionVerdict | None" = None,
        wrong_test : "int | None" = None):
        with transaction.atomic():
            updates = {}
            if status  is not None: updates['status']  = status
            if verdict is not None: updates['verdict'] = verdict
            if wrong_test is not None:
                updates['first_wrong_test'] = wrong_test

            rows_updated = Submission.objects \
                .filter(pk = submission_pk) \
                .update(**updates)
            
            if rows_updated == 0:
                raise Submission.DoesNotExist(
                    f"Could not set submission information for pk={submission_pk}")
            
        # TODO notify channel of change
