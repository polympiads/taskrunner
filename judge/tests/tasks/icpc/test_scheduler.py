
import unittest
from unittest.mock import AsyncMock, Mock, patch

import django.test

from django.contrib.auth.models import User
from django.test import override_settings
from judge.languages import LanguageKind
from judge.tasks.icpc.compile import CompilationResult
from judge.tasks.icpc.scheduler import scheduler_task
from problems.models.problem import Problem
from storecli.error import DownloadError
from submit.models.status import SubmissionStatus
from submit.models.submission import Submission
from taskrunner.celery import judge_app
from typing import List

from judge.tasks.icpc.subinfo import SubmissionInformation
from judge.tasks.icpc.testoutput import TestCaseOutput, TestCasesOutput, flatten_test_cases_output
from submit.models.verdict import SubmissionVerdict, TestCaseVerdict

import pytest

class eager_celery:
    def __enter__ (self):
        self.task_always_eager = judge_app.conf.task_always_eager
        self.task_eager_propagates = judge_app.conf.task_eager_propagates
        judge_app.conf.task_always_eager = True
        judge_app.conf.task_eager_propagates = True
    def __exit__ (self, *args):
        judge_app.conf.task_always_eager = self.task_always_eager
        judge_app.conf.task_eager_propagates = self.task_eager_propagates

def _custom_run_tests_task (
        tests_already_done: List[TestCasesOutput],
        submission: SubmissionInformation,
        test_cases: List[int]
    ):
    pass
def _custom_finalize_task (
        test_cases      : List[TestCasesOutput],
        submission_info : SubmissionInformation
    ):
    pass

@judge_app.task
def custom_run_tests_task (
        tests_already_done: List[TestCasesOutput],
        submission: SubmissionInformation,
        test_cases: List[int]
    ):
    _custom_run_tests_task(tests_already_done, submission, test_cases)
    for test_case in test_cases:
        tests_already_done.append( TestCaseOutput(test_case, TestCaseVerdict.SKIPPED) )
    return tests_already_done
@judge_app.task
def custom_finalize_task (
        test_cases      : List[TestCasesOutput],
        submission_info : SubmissionInformation
    ):
    _custom_finalize_task(test_cases, submission_info)

class TestScheduler(django.test.TransactionTestCase):
    def setUp (self):
        self.patch_run_tests = patch("judge.tasks.icpc.scheduler.run_tests_task", custom_run_tests_task)
        self.patch_finalize  = patch("judge.tasks.icpc.scheduler.finalize_task", custom_finalize_task)
        self.patch_run_tests.start()
        self.patch_finalize.start()

        self.patch_local_finalize = patch("judge.tests.tasks.icpc.test_scheduler._custom_finalize_task")
        self.finalize = self.patch_local_finalize.start()
        self.patch_local_run = patch("judge.tests.tasks.icpc.test_scheduler._custom_run_tests_task")
        self.run_tests = self.patch_local_run.start()

        self.patch_problemstorage_download = patch("storecli.problems.storage.ProblemStorage.download", new_callable=AsyncMock)
        self.storage = self.patch_problemstorage_download.start()

        usr = User.objects.create_user( "user", password = "pass" )
        sub = Submission.objects.create(
            user = usr,
            problem = Problem.objects.create(problem_location = None),
            language = LanguageKind.CPP_23,

            code_location = "in.cpp",
            exec_location = "in"
        )

        self.pk = sub.pk
    def tearDown(self):
        self.patch_run_tests.stop()
        self.patch_finalize.stop()
        self.patch_local_finalize.stop()
        self.patch_local_run.stop()
        self.patch_problemstorage_download.stop()

    def assertSubmission (self, status, verdict):
        sub = Submission.objects.get( pk = self.pk )

        self.assertEqual(sub.status, status)
        self.assertEqual(sub.verdict, verdict)
    def set_number_problems (self, nb_problems: int):
        mock_problem = self.storage.return_value = Mock()
        get_number_tests = mock_problem.get_number_tests = Mock()
        get_number_tests.return_value = nb_problems
    @override_settings(MAX_TESTS_PER_BATCH=3)
    def test_simple_scheduler_compilation_failed (self):
        with eager_celery():
            self.set_number_problems(20)

            subinfo = SubmissionInformation( self.pk, "yes", "yes", LanguageKind.CPP_23 )
            scheduler_task(
                CompilationResult(False, "").serialize(),
                subinfo.serialize()
            )

            self.finalize.assert_not_called()
            self.run_tests.assert_not_called()

            self.assertSubmission( SubmissionStatus.STARTING, SubmissionVerdict.PENDING )
    @override_settings(MAX_TESTS_PER_BATCH=3)
    def test_simple_scheduler (self):
        with eager_celery():
            self.set_number_problems(20)

            subinfo = SubmissionInformation( self.pk, "yes", "yes", LanguageKind.CPP_23 )
            scheduler_task(
                CompilationResult().serialize(),
                subinfo.serialize()
            )

            self.finalize.assert_called_once()
            batch, new_subinfo = self.finalize.call_args.args
            new_subinfo = SubmissionInformation.deserialize(new_subinfo)
            self.assertEqual(subinfo.submission_id, new_subinfo.submission_id)
            self.assertEqual(subinfo.exec_location, new_subinfo.exec_location)
            self.assertEqual(subinfo.problem_location, new_subinfo.problem_location)
            self.assertEqual(subinfo.language, new_subinfo.language)
            
            batch = flatten_test_cases_output(batch)
            batch.sort()

            assert len(batch) == 20
            for i, b in enumerate( batch ):
                assert i == b.test_id
                assert b.verdict == TestCaseVerdict.SKIPPED

            self.run_tests.assert_called()
            
            all_tests_calls = []
            for call in self.run_tests.call_args_list:
                done, sub, tests = call.args
                all_tests_calls.extend(tests)
                assert len(tests) <= 3
            assert len(all_tests_calls) == len(set(all_tests_calls)) == 20
            assert set(all_tests_calls).issubset( list(range(20)) )

            self.assertSubmission( SubmissionStatus.RUNNING, SubmissionVerdict.PENDING )
    @override_settings(MAX_TESTS_PER_BATCH=3)
    def test_scheduler_failure (self):
        with eager_celery():
            self.storage.side_effect = DownloadError("Failure")

            subinfo = SubmissionInformation( self.pk, "yes", "yes", LanguageKind.CPP_23 )
            with self.assertRaises(DownloadError):
                scheduler_task(
                    CompilationResult().serialize(),
                    subinfo.serialize()
                )
                
            self.assertSubmission( SubmissionStatus.FAILED, SubmissionVerdict.JUDGE_ERROR )