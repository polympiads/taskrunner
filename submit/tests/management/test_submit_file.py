
import os
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

class TestSubmitFileManager (TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def mkfile (self, file: str):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), file))

    def test_submit_file_cpp_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_cpp_aplusb_doesnotexist (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.cpp"), "w") as file:
                file.write(APLUSB_PROG_CPP)
            with self.assertRaises(FileNotFoundError):
                call_command("submit_file", user.pk, problem.pk, self.mkfile("index2.cpp"))
        
            self.assertEqual(len(Submission.objects.all()), 0)
    def test_submit_file_python_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.py"), "w") as file:
                file.write(APLUSB_PROG_PYTHON)
            call_command("submit_file", user.pk, problem.pk, self.mkfile("index.py"))
        
            self.assertEqual(len(Submission.objects.all()), 1)
            submission = Submission.objects.all()[0]
            self.assertEqual( submission.verdict, SubmissionVerdict.ACCEPTED )
    def test_submit_file_unknown_extension_aplusb (self):
        problem = Problem.objects.create()
        user = User.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)
            problem = Problem.objects.get(pk = problem.pk)
            with open(self.mkfile("index.blblblbl"), "w") as file:
                file.write(APLUSB_PROG_PYTHON)
            with self.assertRaises(NotImplementedError):
                call_command("submit_file", user.pk, problem.pk, self.mkfile("index.blblblbl"))
        
            self.assertEqual(len(Submission.objects.all()), 0)
