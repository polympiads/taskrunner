
import os
from typing import Dict
import uuid
import zipfile

import config
from storecli.problems.problem import Problem

class ProblemStorage:
    """
    This cache contains pairs of the form
      archive location <-> Problem(path to unzipped folder)
    """
    cache: Dict[str, Problem] = {}

    @staticmethod
    def allocate_problem_directory ():
        os.makedirs( config.PROBLEM_STORAGE_LOCATION, exist_ok=True )
        
        # do at most 100 tests
        # to avoid a deadlock of the worker
        for _idx in range(100):
            dir_path = os.path.join( config.PROBLEM_STORAGE_LOCATION, str( uuid.uuid4() ) )
            if os.path.exists(dir_path):
                continue

            os.makedirs(dir_path)
            return dir_path
        
        # this should never happen, but still report it
        # (in the obscure case that something blocks)
        assert False, "Allocate problem directory failed"

    @staticmethod
    async def download (archive_location: str) -> Problem:
        if archive_location in ProblemStorage.cache:
            return ProblemStorage.cache[archive_location]
        
        archive_path = await config.STORAGE_CLIENT.download( archive_location )
        problem_dir  = ProblemStorage.allocate_problem_directory()

        archive_ext = os.path.splitext(archive_path)[1]
        
        def handle_zip_archive ():
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall( problem_dir )
        
        if archive_ext == ".zip": handle_zip_archive()
        else: raise NotImplementedError(f"Could not recognize archive extension {archive_ext}")

        problem = await Problem.init( problem_dir )
        ProblemStorage.cache[archive_location] = problem

        return problem
