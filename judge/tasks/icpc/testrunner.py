
import asyncio
import enum
import os
from typing import List

from asgiref.sync import sync_to_async
from django.conf import settings

from judge.error import JudgeError
from judge.languages import get_language
from judge.languages.cpp import GNU_GPP_23
from judge.tasks.icpc.subinfo import SubmissionInformation
from judge.tasks.icpc.testoutput import TestCaseOutput, TestCasesOutput, flatten_test_cases_output, get_test_cases_verdict
from sandbox.context import sandbox_open
from sandbox.sandbox import Sandbox
from storecli.problems.problem import Problem
from storecli.problems.storage import ProblemStorage
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict, TestCaseVerdict
from taskrunner.celery import judge_app
from judge.telemetry import start_as_current_span, judge_logger

async def run_test (
        test: int,
        problem: Problem,
        
        sb_eval:  Sandbox, cmd_eval:  List[str],
        sb_check: Sandbox, cmd_check: List[str],
        
        submission: SubmissionInformation,
        tests_already_done: List[TestCasesOutput]) -> bool:
    with start_as_current_span(f"Submission.run_test#{test}") as run_span:
        test_input  = problem.get_input_file(test)
        test_answer = problem.get_output_file(test)
        
        os.chmod(test_input,  0o644)
        os.chmod(test_answer, 0o644)

        await sb_eval.prepare_for_stdin( test_input, "in.txt" )
        eval_results = await sb_eval.run_sandbox( cmd_eval, stdin="in.txt", stdout="out.txt" )
        test_stdout  = sb_eval.path_relative_to_cwd("out.txt")
        run_span.add_event("Evaluation finished")
        run_span.set_attribute("eval:sandbox:stdout", eval_results.sandbox_stdout)
        run_span.set_attribute("eval:sandbox:stderr", eval_results.sandbox_stderr)
        
        os.chmod(test_stdout, 0o644)
        
        if eval_results.process.returncode != 0:
            if eval_results.statistics.exit_code == 127:
                judge_logger.critical(
                    "Judge Error (error code 127) #%s, likely missing executable",
                    test, extra = { "submission-id": submission.submission_id } )
                raise JudgeError(eval_results, "Probably missing executable")
            if eval_results.statistics.status == "TO":
                judge_logger.info(
                    "Time Limit Exceeded #%s",
                    test, extra = { "submission-id": submission.submission_id } )
                tests_already_done.append( TestCaseOutput( test, TestCaseVerdict.TIME_LIMIT ) )
                return True
            if eval_results.statistics.cg_oom_killed: # only detected if settings.USE_CGROUPS
                judge_logger.info(
                    "Memory Limit Exceeded #%s",
                    test, extra = { "submission-id": submission.submission_id } )
                tests_already_done.append( TestCaseOutput( test, TestCaseVerdict.MEM_LIMIT ) )
                return True
            if eval_results.statistics.status in ["RE", "SG"]:
                judge_logger.info(
                    "Runtime Error #%s",
                    test, extra = { "submission-id": submission.submission_id } )
                tests_already_done.append( TestCaseOutput( test, TestCaseVerdict.RUNTIME_ERROR ) )
                return True

            judge_logger.critical(
                "Judge Error (Unknown error) #%s",
                test, extra = { "submission-id": submission.submission_id } )
            raise JudgeError(eval_results, "Unknown evaluation error")

        await sb_check.prepare_for_stdin( test_input,  "prog_in.txt" )
        await sb_check.prepare_for_stdin( test_stdout, "prog_out.txt" )
        await sb_check.prepare_for_stdin( test_answer, "prog_ans.txt" )
        
        check_results = await sb_check.run_sandbox( cmd_check + [ "prog_in.txt", "prog_out.txt", "prog_ans.txt" ] )
        run_span.add_event("Checker finished")
        run_span.set_attribute("checker:sandbox:stdout", check_results.sandbox_stdout)
        run_span.set_attribute("checker:sandbox:stderr", check_results.sandbox_stderr)

        if check_results.process.returncode != 0:
            if check_results.statistics.exit_code in [1, 2]: # Wrong Answer & Presentation Error
                judge_logger.info(
                    "Wrong Answer #%s",
                    test, extra = { "submission-id": submission.submission_id } )
                tests_already_done.append( TestCaseOutput( test, TestCaseVerdict.WRONG_ANSWER ) )
                return True
            if check_results.statistics.exit_code == 127:
                judge_logger.critical(
                    "Judge Error (error code 127) #%s, likely missing checker",
                    test, extra = { "submission-id": submission.submission_id } )
                raise JudgeError(check_results, "Probably missing checker")

            raise JudgeError(check_results, "Unknown checker error")
        
        tests_already_done.append( TestCaseOutput( test, TestCaseVerdict.ACCEPTED ) )

        return False

@judge_app.task
def run_tests_task (
            tests_already_done: List[TestCasesOutput],
            submission: SubmissionInformation,
            test_cases: List[int]
        ) -> List[TestCasesOutput]:
    return asyncio.run( _run_tests_task_and_check_for_errors(tests_already_done, submission, test_cases) )
async def _run_tests_task_and_check_for_errors (
            tests_already_done: List[TestCasesOutput],
            submission: SubmissionInformation,
            test_cases: List[int]
        ) -> List[TestCasesOutput]:
    try:
        return await _run_tests_task(tests_already_done, submission, test_cases)
    except Exception as exc:
        await sync_to_async(Submission.set_submission_information)(
            submission.submission_id,
            SubmissionStatus.FAILED,
            SubmissionVerdict.JUDGE_ERROR)

        raise exc
async def _run_tests_task (
            tests_already_done: List[TestCasesOutput],
            submission: SubmissionInformation,
            test_cases: List[int]
        ) -> List[TestCasesOutput]:
    with start_as_current_span("Submission.run_tests") as root_span:
        tests_already_done = flatten_test_cases_output(tests_already_done)
        root_span.set_attribute("submission:id", submission.submission_id)
        root_span.set_attribute("problem:location", submission.problem_location)
        root_span.set_attribute("executable:location", submission.exec_location)
        root_span.set_attribute("submission:language", submission.language)
        root_span.set_attribute("problem:tests", test_cases)
        root_span.set_attribute("problem:tests-done", list(map(str, tests_already_done)))

        should_skip = get_test_cases_verdict(tests_already_done) != TestCaseVerdict.ACCEPTED

        if should_skip:
            with start_as_current_span("skip_tests") as skip_span:
                for test in test_cases:
                    tests_already_done.append(TestCaseOutput( test, TestCaseVerdict.SKIPPED ))
                root_span.set_attribute("problem:all-tests", list(map(str, tests_already_done)))
                return tests_already_done

        problem = await ProblemStorage.download(submission.problem_location)

        executable = await settings.STORAGE_CLIENT.download(submission.exec_location)
        checker    = problem.get_path("checker")

        os.chmod(checker,    0o755)
        os.chmod(executable, 0o755)

        language = get_language( submission.language )
        
        sb_eval,  cmd_eval  = await language.execute(executable)
        sb_check, cmd_check = await GNU_GPP_23.execute(checker)

        async with sandbox_open(sb_eval), sandbox_open(sb_check):
            for test in test_cases:
                if should_skip:
                    tests_already_done.append( TestCaseOutput(test, TestCaseVerdict.SKIPPED) )
                    continue

                should_skip = await run_test(
                    test,
                    problem,
                    sb_eval, cmd_eval,
                    sb_check, cmd_check,
                    submission,
                    tests_already_done
                )
        
        root_span.set_attribute("problem:all-tests", list(map(str, tests_already_done)))
        return tests_already_done
