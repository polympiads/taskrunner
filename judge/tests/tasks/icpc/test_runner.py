
import os
from typing import List
from unittest.mock import MagicMock, patch
from django.conf import settings
import django.test
from django.test import override_settings

from judge.error import JudgeError
from judge.languages import LanguageKind
from judge.tasks.icpc.compile import CompilationInput, CompilationResult, compile_task
from judge.tasks.icpc.subinfo import SubmissionInformation
from judge.tasks.icpc.testoutput import TestCaseOutput, deserialize_outputs, flatten_test_cases_output, serialize_outputs
from judge.tasks.icpc.testrunner import run_tests_task
from judge.tests.languages.test_cpp import APLUSB_PROG
from problems.models.problem import Problem
from problems.tests.tasks.polygon.test_prepare import compile_polygon_packages, setup_polygon_packages
from sandbox.result import SandboxStatistics
from sandbox.sandbox import Sandbox
from storecli.inmemory import InMemoryStorageClient
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from django.contrib.auth.models import User

from submit.models.verdict import SubmissionVerdict, TestCaseVerdict

# Wrong Answer
APLUSB_PROG_WA = """
#include <iostream>

int main () {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b + 1 << "\\n";
}
"""
# Presentation Error
APLUSB_PROG_PE = """
#include <iostream>

int main () {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << " " << a + b << "\\n";
}
"""
# Runtime Error
APLUSB_PROG_RE = """
#include <iostream>

int dp[10];
int main () {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b + (*(int*)(((long long) dp) - ((long long) dp))) << "\\n";
}
"""
# Memory Limit Exceeded
APLUSB_PROG_MLE = """
#include <iostream>
#include <vector>

int main () {
    int a, b;
    std::vector<int> vect( 70 * 1000 * 1000 );
    std::cin >> a >> b;
    std::cout << a + b + vect[10] << "\\n";
}
"""
# Time Limit Exceeded
APLUSB_PROG_TLE = """
#include <iostream>

const long long MAXI = 1e12;

volatile int a = 0, b = 0;
int main () {
    for (long long i = 0; i < MAXI; i ++) {
        a ++;
        b --;
    }
    int na, nb;
    std::cin >> na >> nb;
    std::cout << a + b + na + nb << "\\n";
}
"""

def custom_mle_read_from (lines: List[str]) -> "SandboxStatistics":
    stats = SandboxStatistics()

    for line in lines:
        line = line.strip()
        if len(line) == 0: continue

        try:
            key, value = line.split(":", maxsplit=1)

            match key:
                case "cg-mem": stats.cg_mem = int(value)
                case "cg-oom-killed": stats.cg_oom_killed = True
                case "csw-forced": stats.csw_forced = int(value)
                case "csw-voluntary": stats.csw_voluntary = int(value)
                case "exitcode": stats.exit_code = int(value)
                case "exitsig": stats.exit_signal = int(value)
                case "killed": stats.killed = True
                case "max-rss": stats.max_memory = int(value)
                case "message": stats.message = value
                case "status": stats.status = value
                case "time": stats.time = float(value)
                case "time-wall": stats.wall_time = float(value)
        except Exception as err:
            raise err
        
    # Mock the cg oom killed
    stats.cg_oom_killed = True
    return stats

class TestTestRunnerTask (django.test.TransactionTestCase):
    def setUp(self):
        self.inmemory_storage = InMemoryStorageClient("/tmp")
        self.patch_storage = override_settings(STORAGE_CLIENT=self.inmemory_storage)
        self.patch_storage.__enter__()

        setup_polygon_packages(self.inmemory_storage)
    def tearDown(self):
        self.patch_storage.__exit__(None, None, None)

    def run_semi_pipeline (self, package: str, code: str, done: List[TestCaseOutput], tests: List[int]):
        input_loc = f"input-{package}"
        exec_loc = f"exec-{package}"

        compile_polygon_packages(package)
        self.inmemory_storage.put(input_loc, code.encode(), ".cpp")
        
        usr = User.objects.create_user( "user", password = "pass" )
        submission = Submission.objects.create(
            user = usr,
            problem = Problem.objects.create(problem_location = None),
            language = LanguageKind.CPP_23,
            code_location = "",
            exec_location = ""
        )

        self.pk = submission.pk
        
        result = CompilationResult.deserialize( compile_task(
            CompilationInput(submission.pk, input_loc, exec_loc, LanguageKind.CPP_23, 1., 1.).serialize()
        ) )
        assert result.compilation_success, result.error_message
        
        subinfo = SubmissionInformation( submission.pk, f"proc-{package}", exec_loc, LanguageKind.CPP_23 )
        return flatten_test_cases_output( deserialize_outputs( run_tests_task(
            serialize_outputs( done ), subinfo.serialize(), tests ) ) )

    def verify_accepted (self, results: List[TestCaseOutput], tests: List[int]):
        for idx, result in enumerate(results):
            self.assertEqual(result.test_id, tests[idx])
            self.assertEqual(result.verdict, TestCaseVerdict.ACCEPTED)
    def verify_failure (self, results: List[TestCaseOutput], tests: List[int], failure: TestCaseVerdict, failure_idx = 0):
        for idx, result in enumerate(results):
            expects = TestCaseVerdict.SKIPPED
            if idx <  failure_idx: expects = TestCaseVerdict.ACCEPTED
            if idx == failure_idx: expects = failure

            self.assertEqual(result.test_id, tests[idx])
            self.assertEqual(result.verdict, expects)

    def test_aplusb_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG, [], list(range(9)) )
        self.verify_accepted(tests_results, list(range(9)))
    def test_aplusb_run_some_done (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG,
            [ [ TestCaseOutput(0, TestCaseVerdict.ACCEPTED) ], TestCaseOutput(1, TestCaseVerdict.ACCEPTED) ],
            list(range(2, 9)) )
        self.verify_accepted(tests_results, list(range(9)))
    def test_aplusb_run_some_missing (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG,
            [ TestCaseOutput(0, TestCaseVerdict.ACCEPTED) ],
            list(range(1, 9, 2)) )
        self.verify_accepted(tests_results, [0] + list(range(1, 9, 2)))
    def test_aplusb_wa_run_some_skipped (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG,
            [ [ TestCaseOutput(0, TestCaseVerdict.ACCEPTED) ], TestCaseOutput(1, TestCaseVerdict.WRONG_ANSWER) ],
            list(range(2, 9)) )
        self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.WRONG_ANSWER, 1)
    def test_aplusb_wa_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_WA, [], list(range(9)) )
        self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.WRONG_ANSWER)
    def test_aplusb_pe_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_PE, [], list(range(9)) )
        self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.WRONG_ANSWER)
    def test_aplusb_re_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_RE, [], list(range(9)) )
        self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.RUNTIME_ERROR)
    def test_aplusb_mle_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_MLE, [], list(range(9)) )
        if settings.USE_CGROUPS:
            self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.MEM_LIMIT)
        else:
            self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.RUNTIME_ERROR)
    def test_aplusb_mle_mock (self):
        with patch ("sandbox.result.SandboxStatistics.read_from", custom_mle_read_from):
            tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_MLE, [], list(range(9)) )
            self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.MEM_LIMIT)
    def test_aplusb_tle_run (self):
        tests_results = self.run_semi_pipeline( "a-plus-b", APLUSB_PROG_TLE, [], list(range(9)) )
        self.verify_failure(tests_results, list(range(9)), TestCaseVerdict.TIME_LIMIT)

    def assertSubmission (self, status, verdict):
        sub = Submission.objects.get( pk = self.pk )

        self.assertEqual(sub.status, status)
        self.assertEqual(sub.verdict, verdict)

    def test_evaluation_missing (self):
        true_run_sandbox = Sandbox.run_sandbox
        async def wrapped_run_sandbox (self: Sandbox, cmd: List[str], *args, **kwargs):
            if cmd[0] != "checker" and cmd[0] != "/usr/bin/g++":
                os.remove( self.path_relative_to_cwd( cmd[0] ) )
            return await true_run_sandbox(self, cmd, *args, **kwargs)
        with patch("sandbox.sandbox.Sandbox.run_sandbox", wrapped_run_sandbox):
            with self.assertRaisesRegex(JudgeError, "Probably missing executable"):
                self.run_semi_pipeline( "a-plus-b", APLUSB_PROG, [], list(range(9)) )
        self.assertSubmission(SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_checker_missing (self):
        true_run_sandbox = Sandbox.run_sandbox
        async def wrapped_run_sandbox (self: Sandbox, cmd: List[str], *args, **kwargs):
            if cmd[0] == "checker":
                os.remove( self.path_relative_to_cwd( cmd[0] ) )
            return await true_run_sandbox(self, cmd, *args, **kwargs)
        with patch("sandbox.sandbox.Sandbox.run_sandbox", wrapped_run_sandbox):
            with self.assertRaisesRegex(JudgeError, "Probably missing checker"):
                self.run_semi_pipeline( "a-plus-b", APLUSB_PROG, [], list(range(9)) )
        self.assertSubmission(SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_evaluation_unexpected_failure (self):
        true_run_sandbox = Sandbox.run_sandbox
        async def wrapped_run_sandbox (self: Sandbox, cmd: List[str], *args, **kwargs):
            result = await true_run_sandbox(self, cmd, *args, **kwargs)
            if cmd[0] == "/usr/bin/g++":
                return result

            result.statistics.status = "XX"
            result.process = MagicMock( returncode=1 )
            result.statistics.exit_code = 25

            return result
        with patch("sandbox.sandbox.Sandbox.run_sandbox", wrapped_run_sandbox):
            with self.assertRaisesRegex(JudgeError, "Unknown evaluation error"):
                self.run_semi_pipeline( "a-plus-b", APLUSB_PROG, [], list(range(9)) )
        self.assertSubmission(SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)
    def test_checker_unexpected_failure (self):
        true_run_sandbox = Sandbox.run_sandbox
        async def wrapped_run_sandbox (self: Sandbox, cmd: List[str], *args, **kwargs):
            result = await true_run_sandbox(self, cmd, *args, **kwargs)
            if cmd[0] != "checker":
                return result

            result.statistics.status = "XX"
            result.process = MagicMock( returncode=1 )
            result.statistics.exit_code = 25

            return result
        with patch("sandbox.sandbox.Sandbox.run_sandbox", wrapped_run_sandbox):
            with self.assertRaisesRegex(JudgeError, "Unknown checker error"):
                self.run_semi_pipeline( "a-plus-b", APLUSB_PROG, [], list(range(9)) )
        self.assertSubmission(SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR)