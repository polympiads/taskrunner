
import asyncio
import json
import os
import unittest
from unittest.mock import patch
import zipfile

import config
from storecli.inmemory import InMemoryStorageClient
from storecli.problems.storage import ProblemStorage


SAMPLE1_PATH = "/tests/sample1.zip"
def prepare_sample1 ():
    if os.path.exists(SAMPLE1_PATH): return

    os.makedirs(os.path.dirname(SAMPLE1_PATH), exist_ok=True)

    with zipfile.ZipFile(SAMPLE1_PATH, "w") as file:
        file.writestr("01.in", "42\n")
        file.writestr("01.out", "43\n")
        file.writestr("problem.json", json.dumps({
            "tests"       : [ { "input": "01.in", "output": "01.out" } ],
            "checker"     : "checker", # checker isn't in the zip as this is sample
            "interactive" : False
        }))

class TestProblemDownload (unittest.IsolatedAsyncioTestCase):
    def setUp (self):
        prepare_sample1()
        self.inmemory_storage = InMemoryStorageClient( "/tmp" )

        self.patch_storage = patch("config.STORAGE_CLIENT", self.inmemory_storage)
        self.patch_storage.start()
        
        ProblemStorage.cache = {}
        asyncio.run( self.inmemory_storage.upload(SAMPLE1_PATH, "sample1") )
        asyncio.run( self.inmemory_storage.upload(SAMPLE1_PATH, "sample1-bis") )
        asyncio.run( self.inmemory_storage.upload(__file__, "not-a-zip") )
    def tearDown(self):
        self.patch_storage.stop()
    
    async def test_download (self):
        problem = await ProblemStorage.download("sample1")

        self.assertEqual(problem.get_number_tests(), 1)
        self.assertEqual(problem.get_input_file(0), os.path.join( problem.problem_dir, "01.in") )
        self.assertEqual(problem.get_output_file(0), os.path.join( problem.problem_dir, "01.out") )
    async def test_download_twice (self):
        problem1 = await ProblemStorage.download("sample1")
        problem2 = await ProblemStorage.download("sample1")

        self.assertEqual(problem1.problem_dir, problem2.problem_dir)
    async def test_allocate_dir_fails (self):
        patch_uuid = patch("uuid.uuid4")
        uuid4 = patch_uuid.start()
        uuid4.return_value = "directory"
        
        problem1 = await ProblemStorage.download("sample1")
        self.assertEqual(problem1.problem_dir, os.path.join(config.PROBLEM_STORAGE_LOCATION, "directory"))
        with self.assertRaises(AssertionError):
            await ProblemStorage.download("sample1-bis")
        patch_uuid.stop()
    async def test_download_not_zip (self):
        with self.assertRaisesRegex(NotImplementedError, f"Could not recognize archive extension \\.py"):
            await ProblemStorage.download("not-a-zip")
