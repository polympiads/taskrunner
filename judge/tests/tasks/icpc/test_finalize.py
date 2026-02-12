
import unittest

import django.test
from django.contrib.auth.models import User
from judge.tasks.icpc.finalize import finalize_task
from judge.tasks.icpc.subinfo import SubmissionInformation
from judge.tasks.icpc.testoutput import TestCaseOutput
from submit.models import Submission
from submit.models.status import SubmissionStatus
from submit.models.verdict import SubmissionVerdict, TestCaseVerdict

class TestFinalizeTask (django.test.TransactionTestCase):
    def setUp(self):
        usr = User.objects.create_user( "user", password = "pass" )
        sub = Submission.objects.create(
            user = usr,

            code_location = "in.cpp",
            exec_location = "in"
        )

        self.pk = sub.pk

    def assertSubmission (self, status, verdict, wrong_test):
        sub = Submission.objects.get( pk = self.pk )

        self.assertEqual(sub.status, status)
        self.assertEqual(sub.verdict, verdict)
        self.assertEqual(sub.first_wrong_test, wrong_test)

    def test_finalize_does_not_exit (self):
        with self.assertRaises(Submission.DoesNotExist):
            finalize_task(
                [ TestCaseOutput(0, TestCaseVerdict.ACCEPTED) ],
                SubmissionInformation( self.pk + 1, "", "", None )
            )
    def test_finalize_accepted (self):
        finalize_task(
            [
                TestCaseOutput(0, TestCaseVerdict.ACCEPTED),
                TestCaseOutput(1, TestCaseVerdict.ACCEPTED)
            ],
            SubmissionInformation( self.pk, "", "", None )
        )

        self.assertSubmission(
            SubmissionStatus.FINISHED, SubmissionVerdict.ACCEPTED, -1 )
    def test_finalize_wrong (self):
        for kind in [ TestCaseVerdict.WRONG_ANSWER, TestCaseVerdict.JUDGE_ERROR,
                     TestCaseVerdict.TIME_LIMIT, TestCaseVerdict.MEM_LIMIT,
                     TestCaseVerdict.RUNTIME_ERROR ]:
            finalize_task(
                [
                    TestCaseOutput(0, TestCaseVerdict.ACCEPTED),
                    TestCaseOutput(1, kind)
                ],
                SubmissionInformation( self.pk, "", "", None )
            )

            self.assertSubmission(
                SubmissionStatus.FINISHED, SubmissionVerdict.fromTestVerdict(kind), 1 )
    def test_two_wrong_same (self):
        for kind in [ TestCaseVerdict.WRONG_ANSWER, TestCaseVerdict.JUDGE_ERROR,
                     TestCaseVerdict.TIME_LIMIT, TestCaseVerdict.MEM_LIMIT,
                     TestCaseVerdict.RUNTIME_ERROR ]:
            finalize_task(
                [
                    TestCaseOutput(0, kind),
                    TestCaseOutput(1, kind)
                ],
                SubmissionInformation( self.pk, "", "", None )
            )

            self.assertSubmission(
                SubmissionStatus.FINISHED, SubmissionVerdict.fromTestVerdict(kind), 0 )
    def test_two_wrong_diff (self):
        finalize_task(
            [
                TestCaseOutput(0, TestCaseVerdict.MEM_LIMIT),
                TestCaseOutput(1, TestCaseVerdict.RUNTIME_ERROR)
            ],
            SubmissionInformation( self.pk, "", "", None )
        )

        self.assertSubmission(
            SubmissionStatus.FINISHED,
            SubmissionVerdict.MEM_LIMIT,
            0 )

        finalize_task(
            [
                [ [ TestCaseOutput(0, TestCaseVerdict.RUNTIME_ERROR) ] ],
                TestCaseOutput(1, TestCaseVerdict.MEM_LIMIT)
            ],
            SubmissionInformation( self.pk, "", "", None )
        )

        self.assertSubmission(
            SubmissionStatus.FINISHED,
            SubmissionVerdict.RUNTIME_ERROR,
            0 )
