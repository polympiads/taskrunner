
import asyncio
import os
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.management import call_command

from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from storecli.inmemory import InMemoryStorageClient
from storecli.problems.storage import ProblemStorage

tests_folder = os.path.dirname(os.path.dirname(__file__))
APLUSB_FILE = os.path.join(tests_folder, "tasks", "polygon", "assets", "a-plus-b.zip")
from django.conf import settings

class TestPreparePolygonCommand (TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient(settings.STORAGE_CLIENT_LOCATION)
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def test_file_does_not_exit (self):
        problem = Problem.objects.create()

        with self.assertRaises(FileNotFoundError):
            call_command("prepare_polygon", problem.pk, "doesnotexit.zip")
    def test_file_exists (self):
        problem = Problem.objects.create()

        with eager_celery():
            call_command("prepare_polygon", problem.pk, APLUSB_FILE)

        problem = Problem.objects.get(pk = problem.pk)
        self.assertIsNotNone(problem.problem_location, None)

        problem = asyncio.run( ProblemStorage.download(problem.problem_location) )

        self.assertEqual( problem.get_number_tests(), 9 )

        for idx in range (problem.get_number_tests()):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))
