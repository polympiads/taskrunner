
import asyncio
import os
from django.conf import settings
from django.core.management import BaseCommand
from django.contrib.auth.models import User

from judge.languages import LanguageKind
from problems.models.preparation import Preparation
from problems.models.problem import Problem
from problems.telemetry import start_as_current_span
from submit.models.submission import Submission

class Command (BaseCommand):
    help = "Create a submission"

    def add_arguments(self, parser):
        parser.add_argument("user_id",    type=int, help="The ID of the user")
        parser.add_argument("problem_id", type=int, help="The ID of the problem")
        parser.add_argument("submission", type=str, help="Path of the file")

    def handle(self, *args, **options):
        user_id    = options['user_id']
        problem_id = options['problem_id']
        submission = options['submission']

        user    = User.objects.get(pk = user_id)
        problem = Problem.objects.get(pk = problem_id)
        
        if not os.path.exists(submission):
            raise FileNotFoundError(f"Could not find submission code: {submission}")

        async def run_upload_submission ():
            location = settings.STORAGE_CLIENT.reserve()

            await settings.STORAGE_CLIENT.upload(submission, location)

            return location

        with start_as_current_span("Submit.file"):
            code_location = asyncio.run(run_upload_submission())

            Submission.objects.create_submission(
                user,
                problem,
                code_location,
                LanguageKind.PYTHON # TODO automatically determine the LanguageKind
            )
