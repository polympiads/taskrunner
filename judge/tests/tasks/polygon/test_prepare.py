
import asyncio
import subprocess
import os
import django.test
from django.test import override_settings

from judge.error import JudgeError
from judge.tasks.polygon.prepare import prepare_polygon_problem
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

def setup_polygon_packages (storage: BaseStorageClient):
    for (location, path) in TEST_POLYGON_PACKAGES:
        abs_path = os.path.join( os.path.dirname(__file__), "assets", path )
        
        asyncio.run( storage.upload(abs_path, location) )
def compile_polygon_packages (proc_target = None):
    for proc in PROCESS_PACKAGES:
        if proc_target is None or proc == proc_target:
            asyncio.run( prepare_polygon_problem( -1000, proc, "proc-" + proc ) )

class TestPreparePolygonProblem (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        setup_polygon_packages(self.inmemory_storage)
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def test_load_hc2_2025_a1_invalid (self):
        with self.assertRaises(RuntimeError):
            asyncio.run( prepare_polygon_problem( -1000, "hc2-2025-A1-invalid-checker", "proc-hc2-2025-A1-invalid-checker" ) )
    def test_load_hc2_2025_a1 (self):
        asyncio.run( prepare_polygon_problem( -1000, "hc2-2025-A1", "proc-hc2-2025-A1" ) )
        problem = asyncio.run( ProblemStorage.download("proc-hc2-2025-A1") )

        self.assertEqual( problem.get_number_tests(), 19 )

        for idx in range (19):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))
    def test_load_a_plus_b (self):
        asyncio.run( prepare_polygon_problem( -1000, "a-plus-b", "proc-a-plus-b" ) )
        problem = asyncio.run( ProblemStorage.download("proc-a-plus-b") )

        self.assertEqual( problem.get_number_tests(), 9 )

        for idx in range (problem.get_number_tests()):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))

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
