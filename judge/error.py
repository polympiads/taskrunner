
from sandbox.result import SandboxResult

class JudgeError (Exception):
    results: SandboxResult

    def __init__(self, results: SandboxResult, *args):
        super().__init__(*args)

        self.results = results
