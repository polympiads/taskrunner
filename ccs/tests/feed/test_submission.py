
from django.test import TestCase

from submit.models.status import SubmissionStatus, submission_status_to_string


class TestSubmissionFeed (TestCase):
    def test_submission_status_to_string (self):
        self.assertEqual( submission_status_to_string(SubmissionStatus.STARTING), "starting")
        self.assertEqual( submission_status_to_string(SubmissionStatus.COMPILING), "compiling")
        self.assertEqual( submission_status_to_string(SubmissionStatus.RUNNING), "running")
        self.assertEqual( submission_status_to_string(SubmissionStatus.FINISHED), "finished")
        self.assertEqual( submission_status_to_string(SubmissionStatus.FAILED), "failed")

        with self.assertRaises(NotImplementedError):
            submission_status_to_string(None)
