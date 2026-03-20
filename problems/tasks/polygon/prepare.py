
import asyncio
import json
import os
import shutil
import sys
import tempfile
import zipfile
import aiofiles

from ccs.feed.problems import create_problem_event
from ccs.models.contest import ContestProblem
from taskrunner.celery import judge_app
from problems.telemetry import start_as_current_span
from asgiref.sync import sync_to_async, async_to_sync
from django.conf import settings

from judge.languages.cpp import GNU_GPP_23
from problems.models.preparation import Preparation, PreparationStatus
from problems.tasks.polygon.pgformat.problem import read_polygon_problem, PolygonProblem
from sandbox.sandbox import Sandbox
from storecli.problems.problem import ProblemMetadata

def run_problems_copy (unzippedFolder: str, resultFolder: str, problem: PolygonProblem, metadata: ProblemMetadata):
    with start_as_current_span("copy statements"):
        shutil.copy( os.path.join(unzippedFolder, problem.statement), os.path.join( resultFolder, "statement.pdf" ) )
    with start_as_current_span("copy problems"):
        os.mkdir( os.path.join( resultFolder, "tests" ) )

        def copy_test (name: str):
            basename = os.path.basename(name)
            inpath = os.path.join("tests", basename)

            shutil.copy( os.path.join(unzippedFolder, name), os.path.join( resultFolder, inpath ) )

            return inpath
        
        for input, answer in problem.tests:
            metadata["tests"].append({ "input": copy_test(input), "output": copy_test(answer) })

async def run_checker_compilation (unzippedFolder: str, resultFolder: str, problem: PolygonProblem):
    with start_as_current_span("compile checker"):
        # copy testlib.h
        async def copy_testlib_in_sandbox (sandbox: "Sandbox"):
            testlib_inside = sandbox.path_relative_to_cwd( "testlib.h" )
            testlib_out    = os.path.join(unzippedFolder, "files/testlib.h")

            os.link(testlib_out, testlib_inside)
        
        success, result, errmsg = await GNU_GPP_23.compile(
            os.path.join(unzippedFolder, problem.checker),
            os.path.join(resultFolder, "checker"),
            copy_testlib_in_sandbox
        )

        if not success:
            raise Exception("Compilation error for checker.")

@judge_app.task
def prepare_polygon_problem (
        problem_id      : int,
        preparation_id  : int,
        polygon_pkg_loc : str,
        target_loc      : str
    ):
    try:
        return async_to_sync(_prepare_polygon_problem)(problem_id, preparation_id, polygon_pkg_loc, target_loc)
    except Exception as exc:
        Preparation.objects.set_preparation_status(preparation_id, PreparationStatus.FAILURE)

        raise exc

async def _prepare_polygon_problem (
        problem_id      : int,
        preparation_id  : int,
        polygon_pkg_loc : str,
        target_loc      : str
    ):
    with start_as_current_span("Problem.prepare:polygon") as span:
        span.set_attribute("problem:id", problem_id)
        span.set_attribute("problem:polygon-package", polygon_pkg_loc)
        span.set_attribute("problem:target-loc", target_loc)
        span.set_attribute("preparation:id", preparation_id)

        await sync_to_async(Preparation.objects.set_preparation_status)(
            preparation_id, PreparationStatus.RUNNING )
        pkg_path = await settings.STORAGE_CLIENT.download(polygon_pkg_loc)

        with tempfile.TemporaryDirectory(prefix = settings.TEMPDIR_STORAGE_LOCATION) as tmpdir:
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
            metadata["time_limit"] = problem.timelimit
            metadata["memory_limit"] = problem.memlimit
            metadata["name"] = problem.name

            await asyncio.gather(
                sync_to_async(run_problems_copy)(unzippedFolder, resultFolder, problem, metadata),                 
                run_checker_compilation( unzippedFolder, resultFolder, problem ))
            async with aiofiles.open( os.path.join(resultFolder, "problem.json"), "w" ) as file:
                await file.write(json.dumps(metadata))

            def zip_back ():
                shutil.make_archive(resultFilename, 'zip', resultFolder)

            await sync_to_async(zip_back)()
            await settings.STORAGE_CLIENT.upload(resultFile, target_loc)
            
            await sync_to_async(Preparation.objects.finish_preparation)( preparation_id, target_loc, problem_id )
            
            async for contest_pb in ContestProblem.objects \
                    .select_related("contest") \
                    .filter(problem_id = problem_id):
                await create_problem_event(
                    contest_pb.contest,
                    problem_id,
                    contest_pb.label,
                    metadata["name"],
                    metadata["time_limit"],
                    metadata["memory_limit"] // 1024, # mem_limit in KiB to MiB
                    preparation_id
                )
