
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings

from judge.languages import LanguageKind
from judge.tests.languages.test_cpp import APLUSB_PROG as APLUSB_PROG_CPP
from judge.tests.languages.test_python import APLUSB_PROG as APLUSB_PROG_PYTHON
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from django.core.management import call_command
from django.contrib.auth.models import User

from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from storecli.inmemory import InMemoryStorageClient
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict

from taskrunner.celery import judge_app
from django.conf import settings

class TestSubmissionManager (TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient(settings.STORAGE_CLIENT_LOCATION)
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)
    
    def test_create_submission_cpp_aplusb (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
        
            code_location = self.inmemory_storage.reserve()
            self.inmemory_storage.put(code_location, APLUSB_PROG_CPP.encode(), ".cpp")
            submission = Submission.objects.create_submission(
                User.objects.create(),
                problem,
                code_location,
                LanguageKind.CPP_23
            )

            submission = Submission.objects.get(pk = submission.pk)
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_create_submission_python_aplusb (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
        
            code_location = self.inmemory_storage.reserve()
            self.inmemory_storage.put(code_location, APLUSB_PROG_PYTHON.encode(), ".py")
            submission = Submission.objects.create_submission(
                User.objects.create(),
                problem,
                code_location,
                LanguageKind.PYTHON
            )

            submission = Submission.objects.get(pk = submission.pk)
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
