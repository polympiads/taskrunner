
from django.test import TestCase

from ccs.feed.judgetype import JudgementType
from submit.models.verdict import SubmissionVerdict


class TestJudgementFeed (TestCase):
    def test_verdict_to_judgement (self):
        self.assertEqual(JudgementType.AC, JudgementType.from_verdict(SubmissionVerdict.ACCEPTED))
        self.assertEqual(JudgementType.CE, JudgementType.from_verdict(SubmissionVerdict.COMPILER_ERROR))
        self.assertEqual(JudgementType.JE, JudgementType.from_verdict(SubmissionVerdict.JUDGE_ERROR))
        self.assertEqual(JudgementType.MLE, JudgementType.from_verdict(SubmissionVerdict.MEM_LIMIT))
        self.assertEqual(JudgementType.TLE, JudgementType.from_verdict(SubmissionVerdict.TIME_LIMIT))
        self.assertEqual(JudgementType.RE, JudgementType.from_verdict(SubmissionVerdict.RUNTIME_ERROR))
        self.assertEqual(JudgementType.WA, JudgementType.from_verdict(SubmissionVerdict.WRONG_ANSWER))
    
        with self.assertRaises(NotImplementedError):
            JudgementType.from_verdict(None)

