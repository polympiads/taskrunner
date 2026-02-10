
import asyncio
import os
import django.test
from django.test import override_settings

from judge.tasks.polygon.prepare import prepare_polygon_problem
from storecli.inmemory import InMemoryStorageClient
from storecli.problems.storage import ProblemStorage

TEST_POLYGON_PACKAGES = [
    ("hc2-2025-A1", "hc2_2025_A1.zip")
]

class TestPreparePolygonProblem (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        for (location, path) in TEST_POLYGON_PACKAGES:
            abs_path = os.path.join( os.path.dirname(__file__), "assets", path )
            
            asyncio.run( self.inmemory_storage.upload(abs_path, location) )
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def test_load_hc2_2025_a1 (self):
        asyncio.run( prepare_polygon_problem( -1000, "hc2-2025-A1", "proc-hc2-2025-A1" ) )
        problem = asyncio.run( ProblemStorage.download("proc-hc2-2025-A1") )

        self.assertEqual( problem.get_number_tests(), 19 )

        for idx in range (19):
            self.assertEqual( problem.get_input_file(idx), problem.get_path("tests/%02d" % (idx + 1)) )
            self.assertEqual( problem.get_output_file(idx), problem.get_path("tests/%02d.a" % (idx + 1)) )
        
        self.assertTrue(os.path.exists(problem.get_path("checker")))
