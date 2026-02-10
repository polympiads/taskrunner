
from typing import List
from judge.tasks.icpc.subinfo import SubmissionInformation
from judge.tasks.icpc.testoutput import TestCasesOutput, as_string_buffer, flatten_test_cases_output
from judge.telemetry import start_as_current_span
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict, TestCaseVerdict
from taskrunner.celery import judge_app

@judge_app.task
def finalize_task (
        test_cases      : List[TestCasesOutput],
        submission_info : SubmissionInformation
    ):
    with start_as_current_span(f"Submission.finalize") as span:
        span.set_attribute("submission:id", submission_info.submission_id)
        span.set_attribute("storage:exec", submission_info.exec_location)
        span.set_attribute("storage:problem", submission_info.problem_location)
        
        flattened_tests = flatten_test_cases_output(test_cases)
        flattened_tests.sort()
        
        span.set_attribute("execute:verdicts", as_string_buffer(flattened_tests))

        tests_verdict = TestCaseVerdict.ACCEPTED
        
        target_test = None
        for test in flattened_tests:
            if test.verdict != TestCaseVerdict.ACCEPTED:
                target_test = test.test_id
                tests_verdict = test.verdict
                span.set_attribute("execute:first-wrong", target_test)
                break
        
        submission_verdict = SubmissionVerdict.fromTestVerdict(tests_verdict)

        span.set_attribute("execute:global-verdict", str(submission_verdict))

        Submission.set_submission_information(
            submission_info.submission_id,
            status  = SubmissionStatus.FINISHED,
            verdict = submission_verdict,
            wrong_test = target_test
        )
