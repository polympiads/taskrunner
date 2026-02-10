
import asyncio
import json
import os
import shutil
import tempfile
import zipfile
import aiofiles
from asgiref.sync import sync_to_async
from django.conf import settings

from judge.languages.cpp import GNU_GPP_23
from judge.tasks.polygon.pgformat.problem import read_polygon_problem
from sandbox.sandbox import Sandbox
from storecli.problems.problem import ProblemMetadata

async def prepare_polygon_problem (
        problem_id      : int,
        polygon_pkg_loc : str,
        target_loc      : str
    ):
    pkg_path = await settings.STORAGE_CLIENT.download(polygon_pkg_loc)

    with tempfile.TemporaryDirectory() as tmpdir:
        unzippedFolder = os.path.join(tmpdir, "polygon")
        resultFolder = os.path.join(tmpdir, "problem")
        resultFile = os.path.join(tmpdir, "result.zip")
        resultFilename = os.path.join(tmpdir, "result")

        os.mkdir(resultFolder)

        def run_extract ():
            with zipfile.ZipFile(pkg_path, "r") as zip:
                zip.extractall(unzippedFolder)
        
        await sync_to_async(run_extract)()
        problem = await sync_to_async(read_polygon_problem)( os.path.join(unzippedFolder, "problem.xml") )

        metadata: ProblemMetadata = { "tests": [] }
        def run_problems_copy ():
            os.mkdir( os.path.join( resultFolder, "tests" ) )

            def copy_test (name: str):
                basename = os.path.basename(name)
                inpath = os.path.join("tests", basename)

                shutil.copy( os.path.join(unzippedFolder, name), os.path.join( resultFolder, inpath ) )

                return inpath
            
            for input, answer in problem.tests:
                metadata["tests"].append({ "input": copy_test(input), "output": copy_test(answer) })
        
        run_problems_copy = sync_to_async(run_problems_copy)
        async def run_checker_compilation ():
            # copy testlib.h
            async def copy_testlib_in_sandbox (sandbox: "Sandbox"):
                testlib_inside = sandbox.path_relative_to_cwd( "testlib.h" )
                testlib_out    = os.path.join(unzippedFolder, "files/testlib.h")

                os.link(testlib_out, testlib_inside)
            
            success, result = await GNU_GPP_23.compile(
                os.path.join(unzippedFolder, problem.checker),
                os.path.join(resultFolder, "checker"),
                copy_testlib_in_sandbox
            )

            if not success:
                raise RuntimeError("Compilation error for checker.")

        await asyncio.gather(run_problems_copy(), run_checker_compilation())
        async with aiofiles.open( os.path.join(resultFolder, "problem.json"), "w" ) as file:
            await file.write(json.dumps(metadata))

        def zip_back ():
            shutil.make_archive(resultFilename, 'zip', resultFolder)

        await sync_to_async(zip_back)()
        await settings.STORAGE_CLIENT.upload(resultFile, target_loc)
