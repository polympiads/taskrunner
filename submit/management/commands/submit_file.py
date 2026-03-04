
import asyncio
import os
from django.conf import settings
from django.core.management import BaseCommand
from django.contrib.auth.models import User

from ccs.models.contest import Contest
from judge.languages import LanguageKind, get_language_kind_from_extension
from problems.models.preparation import Preparation
from problems.models.problem import Problem
from problems.telemetry import start_as_current_span
from submit.models.submission import Submission
from asgiref.sync import async_to_sync

def submit_file (
        user       : "User",
        problem    : "Problem",
        submission : str,

        contest : "Contest | None" = None
    ):
    async def run_upload_submission ():
        location = settings.STORAGE_CLIENT.reserve()

        await settings.STORAGE_CLIENT.upload(submission, location)

        return location

    with start_as_current_span("Submit.file"):
        code_location = async_to_sync(run_upload_submission)()

        return Submission.objects.create_submission(
            user,
            problem,
            code_location,
            get_language_kind_from_extension(
                os.path.splitext(submission)[1]
            ),
            contest = contest
        ).pk

class Command (BaseCommand):
    help = "Create a submission"

    def add_arguments(self, parser):
        parser.add_argument("user_id",    type=int, help="The ID of the user")
        parser.add_argument("problem_id", type=int, help="The ID of the problem")
        parser.add_argument("submission", type=str, help="Path of the file")
        parser.add_argument("--contest",  type=int, help="The contest to submit on")

    def handle(self, *args, **options):
        user_id    = options['user_id']
        problem_id = options['problem_id']
        submission = options['submission']

        contest_id = options.get("contest")

        user    = User.objects.get(pk = user_id)
        problem = Problem.objects.get(pk = problem_id)
        contest = None

        if contest_id is not None:
            contest = Contest.objects.get(pk = contest_id)
        
        if not os.path.exists(submission):
            raise FileNotFoundError(f"Could not find submission code: {submission}")

        submit_file(user, problem, submission, contest)
