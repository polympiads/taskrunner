
from functools import cached_property
import json
import os
from typing import List, TypedDict

import aiofiles

class TestMetadata (TypedDict):
    input  : str
    output : str
class ProblemMetadata (TypedDict):
    tests: List[TestMetadata]

class Problem:
    problem_dir  : str
    problem_json : ProblemMetadata

    def get_path (self, path: str):
        return os.path.join(self.problem_dir, path)
    
    @staticmethod
    async def init (problem_dir: str):
        self = Problem()
        self.problem_dir = problem_dir
        
        async with aiofiles.open( self.get_path( "problem.json" ), "r" ) as file:
            json_text = await file.read()
            self.problem_json = json.loads(json_text)

        return self

    def get_input_file (self, test_id: int) -> str:
        return self.get_path( self.problem_json["tests"][test_id]["input"] )
    def get_output_file (self, test_id: int) -> str:
        return self.get_path( self.problem_json["tests"][test_id]["output"] )
    def get_number_tests (self) -> int:
        return len(self.problem_json["tests"])
