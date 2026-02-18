"""
Task Runner :: ICPC Judge

This task is supposed to be the task
scheduling the evaluation of tests.
The objective is to decide how to split
tests into batches such that a WA will
take place in the first batch (likely)
and a TLE in the first or second batch.

The scheduler will split into three groups :
- The WA group, first K test cases
- The TLE group, K to 2K test cases
- The rest, split into batches of size K
"""

import asyncio

from celery import chord
from django.conf import settings
from judge.tasks.icpc.finalize import finalize_task
from judge.tasks.icpc.subinfo import SubmissionInformation, s_SubmissionInformation
from judge.tasks.icpc.testrunner import run_tests_task
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict
from taskrunner.celery import judge_app
from judge.tasks.icpc.compile import CompilationResult, s_CompilationResult
from storecli.problems.storage import ProblemStorage
from judge.telemetry import start_as_current_span, judge_logger
from asgiref.sync import sync_to_async

@judge_app.task
def scheduler_task (
        compilation_result : s_CompilationResult,
        submission_info    : s_SubmissionInformation
        ):
    return _scheduler_task(
        CompilationResult.deserialize(compilation_result),
        SubmissionInformation.deserialize(submission_info))

def _scheduler_task (
        compilation_result : CompilationResult,
        submission_info    : SubmissionInformation
        ):
    with start_as_current_span("Submission.scheduler") as span:
        span.set_attribute("submission:id", submission_info.submission_id)
        span.set_attribute("problem:location", submission_info.problem_location)
        span.set_attribute("executable:location", submission_info.exec_location)
        span.set_attribute("compilation:success", compilation_result.compilation_success)

        if not compilation_result.compilation_success:
            return
        
        try:
            problem = asyncio.run( ProblemStorage.download( submission_info.problem_location ) )
            
            test_count = problem.get_number_tests()
            span.set_attribute("problem:test-count", test_count)

            all_batches = []
            batches_as_strings = []
            for start in range(0, test_count, settings.MAX_TESTS_PER_BATCH):
                end = min(start + settings.MAX_TESTS_PER_BATCH, test_count)

                batch = run_tests_task.s( [], submission_info.serialize(), list(range(start, end)) )
                all_batches.append(batch)

                batches_as_strings.append(f"range({start}, {end})")
            span.set_attribute("evaluation:batches", batches_as_strings)

            Submission.set_submission_information(
                submission_info.submission_id,
                status  = SubmissionStatus.RUNNING
            )

            return chord( all_batches )( finalize_task.s( submission_info.serialize() ) )
        except Exception as exc:
            judge_logger.critical(
                "Scheduling failed for submission id %s",
                submission_info.submission_id
            )

            Submission.set_submission_information(
                submission_info.submission_id,
                status  = SubmissionStatus.FAILED,
                verdict = SubmissionVerdict.JUDGE_ERROR
            )

            raise exc
