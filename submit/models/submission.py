
from typing import TYPE_CHECKING

from celery import chain
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django_enumfield import enum

from ccs.feed.judgement import create_judgement_event
from ccs.feed.judgetype import JudgementType
from ccs.feed.submission import create_contest_start_event, create_contest_state_event
from ccs.models.managers.eventfeed import EventFeedManager, EventFeedKind
from ccs.utils.time import Reltime, Time

if TYPE_CHECKING:
    from ccs.models.contest import Contest

from asgiref.sync import async_to_sync
from ccs.models.eventfeed import EventFeed
from judge.languages import LanguageKind, get_language
from problems.models.problem import Problem
from submit.models.status import SubmissionStatus, submission_status_to_string
from submit.models.verdict import SubmissionVerdict

from django.utils import timezone
from django.db import transaction

class SubmitError (ValueError): pass

class SubmissionManager (models.Manager):
    def create_submission (
        self,
        user    : User,
        problem : Problem,

        code_location : str,

        language_kind : LanguageKind,

        contest : "Contest | None" = None
    ):
        if contest is not None:
            from ccs.models.contest import ContestAccount, ContestRole
            
            contest_account = ContestAccount.objects.filter(contest = contest, user = user)
            if len(contest_account) == 0:
                raise SubmitError("User cannot create a submission in that contest.")
            
            contest_account = contest_account[0]

            if contest_account.role != ContestRole.JUDGE:
                if contest.started is None:
                    raise SubmitError("Cannot create submission for contest that hasn't started.")
                
                current_time = timezone.now()
                delta_time   = current_time - contest.started

                if delta_time > contest.duration:
                    raise SubmitError("Cannot create submission after the end of the contest.")

        with transaction.atomic():
            language = get_language(language_kind)

            exec_location = code_location
            if language.should_compile():
                exec_location = settings.STORAGE_CLIENT.reserve()

            submission = Submission.objects.create(
                user    = user,
                problem = problem,

                code_location = code_location,
                exec_location = exec_location,

                language = language_kind,
                contest = contest
            )

        if contest is not None:
            create_contest_start_event(contest, submission.pk, language_kind, problem.pk, user)
            create_contest_state_event(contest, submission.pk, submission.status, user)

        from judge.tasks.icpc.compile   import compile_task
        from judge.tasks.icpc.scheduler import scheduler_task

        from judge.tasks.icpc.compile import CompilationInput, CompilationResult
        from judge.tasks.icpc.subinfo import SubmissionInformation

        if language.should_compile():
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
        else:
            scheduler_task.delay_on_commit(
                CompilationResult().serialize(),
                SubmissionInformation(
                    submission.pk,
                    problem.problem_location,
                    exec_location,
                    language_kind
                ).serialize()
            )

        return submission

class Submission (models.Model):
    contest = models.ForeignKey(
        "ccs.Contest",
        on_delete=models.PROTECT,
        null=True
    )

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

            submissions = Submission.objects \
                .select_for_update() \
                .filter(pk = submission_pk)
            
            if len(submissions) == 0:
                raise Submission.DoesNotExist(
                    f"Could not set submission information for pk={submission_pk}")

            submission = submissions[0]

            old_status  : SubmissionStatus  = submission.status
            old_verdict : SubmissionVerdict = submission.verdict

            Submission.objects \
                .filter(pk = submission_pk) \
                .update(**updates)
        
        if submission.contest is None:
            return
        
        if status != old_status and status is not None:
            create_contest_state_event(
                submission.contest, submission.pk, status, submission.user
            )
        if verdict != old_verdict and verdict is not None:
            # TODO handle freeze
            create_judgement_event(
                submission.contest, submission.pk, verdict
            )
