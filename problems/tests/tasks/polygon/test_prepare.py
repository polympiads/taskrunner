
import asyncio
import datetime
import json
import subprocess
import os
import django.test
from django.test import override_settings

from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from judge.error import JudgeError
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.preparation import PolygonPreparation, Preparation, PreparationKind, PreparationStatus
from problems.models.problem import Problem
from problems.tasks.polygon.prepare import prepare_polygon_problem
from storecli.base import BaseStorageClient
from storecli.inmemory import InMemoryStorageClient
from storecli.problems.storage import ProblemStorage

TEST_POLYGON_PACKAGES = [
    ("hc2-2025-A1", "hc2_2025_A1.zip"),
    ("hc2-2025-A1-invalid-checker", "hc2_2025_A1_invalid_checker.zip"),
    ("a-plus-b", "a-plus-b.zip")
]
PROCESS_PACKAGES = [
    "a-plus-b"
]

def get_test_package_location (path: str):
    return os.path.abspath( os.path.join( os.path.dirname(__file__), "assets", path ) )

def setup_polygon_packages (storage: BaseStorageClient):
    for (location, path) in TEST_POLYGON_PACKAGES:
        abs_path = os.path.join( os.path.dirname(__file__), "assets", path )
        
        asyncio.run( storage.upload(abs_path, location) )
def compile_polygon_packages (proc_target = None):
    for proc in PROCESS_PACKAGES:
        if proc_target is None or proc == proc_target:
            problem = Problem.objects.create(
                problem_location = None
            )
            preparation = Preparation.objects.create(
                problem = problem,
                storage = "proc-" + proc,
                kind    = PreparationKind.POLYGON,
                status  = PreparationStatus.PENDING
            )
            polygon_preparation = PolygonPreparation.objects.create(
                preparation = preparation,
                pkg_storage = proc
            )
            prepare_polygon_problem( problem.pk, preparation.pk, proc, "proc-" + proc )

class TestPreparePolygonProblem (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        setup_polygon_packages(self.inmemory_storage)

        self.problem = Problem.objects.create(
            problem_location = None
        )
        self.preparation = Preparation.objects.create(
            problem = self.problem,
            storage = "proc-yes",
            kind    = PreparationKind.POLYGON,
            status  = PreparationStatus.PENDING
        )
        self.polygon_preparation = PolygonPreparation.objects.create(
            preparation = self.preparation,
            pkg_storage = "yes"
        )
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def assertProblem (self, status: PreparationStatus):
        problem = Problem.objects.get(pk = self.problem.pk)
        if status == PreparationStatus.SUCCESS:
            self.assertIsNotNone(problem.problem_location)
        else:
            self.assertIsNone(problem.problem_location)
        
        preparation = Preparation.objects.get(pk = self.preparation.pk)
        self.assertEqual(preparation.status, status)

    def test_load_hc2_2025_a1_invalid (self):
        with self.assertRaisesRegex(Exception, "Compilation error for checker."):
            prepare_polygon_problem( self.problem.pk, self.preparation.pk, "hc2-2025-A1-invalid-checker", "proc-hc2-2025-A1-invalid-checker" )
        self.assertProblem(PreparationStatus.FAILURE)
    def test_load_hc2_2025_a1 (self):
        prepare_polygon_problem( self.problem.pk, self.preparation.pk, "hc2-2025-A1", "proc-hc2-2025-A1" )
        problem = asyncio.run( ProblemStorage.download("proc-hc2-2025-A1") )

        self.assertEqual( problem.get_number_tests(), 19 )
        self.assertEqual( problem.get_name(), "Cleopatra's Carpets (Easy)" )

        for idx in range (19):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))
        self.assertProblem(PreparationStatus.SUCCESS)
    def test_load_a_plus_b_wrong_problem_id (self):
        with self.assertRaises( Problem.DoesNotExist ):
            prepare_polygon_problem( self.problem.pk + 1, self.preparation.pk, "a-plus-b", "proc-a-plus-b" )
        self.assertProblem(PreparationStatus.FAILURE)
    def test_load_a_plus_b_wrong_preparation_id (self):
        with self.assertRaises( Preparation.DoesNotExist ):
            prepare_polygon_problem( self.problem.pk, self.preparation.pk + 1, "a-plus-b", "proc-a-plus-b" )
        self.assertProblem(PreparationStatus.PENDING)
    def test_load_a_plus_b (self):
        prepare_polygon_problem( self.problem.pk, self.preparation.pk, "a-plus-b", "proc-a-plus-b" )
        problem = asyncio.run( ProblemStorage.download("proc-a-plus-b") )

        self.assertEqual( problem.get_number_tests(), 9 )
        self.assertEqual( problem.get_name(), "VW50aWwgYSBuZXcgZGF3bg==" )

        for idx in range (problem.get_number_tests()):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))
        self.assertProblem(PreparationStatus.SUCCESS)

        checker_path = problem.get_path("checker")
        os.chmod(checker_path, 0o777)
        for idx in range (problem.get_number_tests()):
            inp_path = problem.get_input_file(idx)
            ans_path = problem.get_output_file(idx)
            out_path = problem.get_input_file(idx) + ".o"

            a, b = 0, 0
            with open(inp_path, "r") as file:
                a, b = map(int, file.read().strip().split())
            true_ans = a + b
            my_ans = (true_ans + (idx % 2))
            with open(out_path, "w") as file:
                file.write(str(my_ans) + "\n")
            
            proc = subprocess.run(
                [ checker_path, inp_path, out_path, ans_path ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            
            if true_ans == my_ans:
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stderr.decode(), f"ok answer is '{true_ans}'\n")
                self.assertEqual(proc.stdout.decode(), f"")
            else:
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stderr.decode(), f"wrong answer expected '{true_ans}', found '{my_ans}'\n")
                self.assertEqual(proc.stdout.decode(), f"")

    def test_create_from_storage (self):
        self.polygon_preparation.delete()
        self.preparation.delete()
        self.problem.delete()

        Problem.objects.create_from_storage("my-storage")

        problems = list( Problem.objects.all() )
        self.assertEqual(len(problems), 1)

        problem = problems[0]
        self.assertEqual(problem.problem_location, "my-storage")
    def test_create_from_polygon (self):
        with eager_celery():
            self.polygon_preparation.delete()
            self.preparation.delete()
            self.problem.delete()
            Problem.objects.create_from_polygon( "a-plus-b" )
            
            self.problem = Problem.objects.all()[0]
            self.preparation = Preparation.objects.all()[0]
            self.polygon_preparation = PolygonPreparation.objects.all()[0]
            problem = asyncio.run( ProblemStorage.download(self.problem.problem_location) )

            self.assertEqual( problem.get_number_tests(), 9 )
            self.assertEqual( problem.get_name(), "VW50aWwgYSBuZXcgZGF3bg==" )

            for idx in range (problem.get_number_tests()):
                self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
                self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
            
            self.assertTrue(os.path.exists(problem.get_path("checker")))
            self.assertProblem(PreparationStatus.SUCCESS)
    def test_create_from_polygon_for_contest (self):
        contest = asyncio.run(ContestManager.acreate_contest(
            visibility = Visibility.PUBLIC,
            name       = "hc2-2025",

            duration = datetime.timedelta(hours = 5),
            penalty_time = datetime.timedelta(minutes = 20)
        ))
        EventFeed.objects.all().delete()
        
        with eager_celery():
            self.polygon_preparation.delete()
            self.preparation.delete()
            self.problem.delete()
            Problem.objects.create_from_polygon_for_contest(
                "a-plus-b",
                contest,
                "A1"
            )
            
            self.problem = Problem.objects.all()[0]
            self.preparation = Preparation.objects.all()[0]
            self.polygon_preparation = PolygonPreparation.objects.all()[0]
            problem = asyncio.run( ProblemStorage.download(self.problem.problem_location) )

            self.assertEqual(len(EventFeed.objects.all()), 1)
            self.assertEqual(
                EventFeed.objects.all()[0] \
                    .contest.pk,
                contest.pk
            )
            self.assertEqual(
                json.loads(EventFeed.objects.all()[0] \
                    .full_payload),
                { "id": str(self.problem.pk), "token": str(EventFeed.objects.all()[0].pk), "type": "problems", 
                 "data": { "id": str(self.problem.pk), "label": "A1", "name": "VW50aWwgYSBuZXcgZGF3bg==",
                    "statement": [{ "mime": "application/pdf",
                        "href": f"/contests/{contest.pk}/problems/{self.problem.pk}/statement/" }],
                    "memory_limit": 238, "time_limit": 1.0, "preparation_id": str(self.polygon_preparation.pk) }}
            )

            self.assertEqual( problem.get_number_tests(), 9 )
            self.assertEqual( problem.get_name(), "VW50aWwgYSBuZXcgZGF3bg==" )

            for idx in range (problem.get_number_tests()):
                self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
                self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
            
            self.assertTrue(os.path.exists(problem.get_path("checker")))
            self.assertTrue(os.path.exists(problem.get_statement()))
            self.assertProblem(PreparationStatus.SUCCESS)
