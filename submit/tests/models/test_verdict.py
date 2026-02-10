
import unittest

from submit.models.verdict import SubmissionVerdict, TestCaseVerdict as TCVerdict

class TestVerdict (unittest.TestCase):
    def test_verdict_order (self):
        self.assertFalse( TCVerdict.SKIPPED < TCVerdict.SKIPPED )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.ACCEPTED )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.TIME_LIMIT )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.MEM_LIMIT )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.RUNTIME_ERROR )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.SKIPPED < TCVerdict.JUDGE_ERROR )
        
        self.assertFalse( TCVerdict.ACCEPTED < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.ACCEPTED < TCVerdict.ACCEPTED )
        self.assertTrue ( TCVerdict.ACCEPTED < TCVerdict.TIME_LIMIT )
        self.assertTrue ( TCVerdict.ACCEPTED < TCVerdict.MEM_LIMIT )
        self.assertTrue ( TCVerdict.ACCEPTED < TCVerdict.RUNTIME_ERROR )
        self.assertTrue ( TCVerdict.ACCEPTED < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.ACCEPTED < TCVerdict.JUDGE_ERROR )
        
        # No order constraint for MEM_LIMIT AND TIME_LIMIT
        self.assertFalse( TCVerdict.TIME_LIMIT < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.TIME_LIMIT < TCVerdict.ACCEPTED )
        self.assertFalse( TCVerdict.TIME_LIMIT < TCVerdict.TIME_LIMIT )
        self.assertTrue ( TCVerdict.TIME_LIMIT < TCVerdict.RUNTIME_ERROR )
        self.assertTrue ( TCVerdict.TIME_LIMIT < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.TIME_LIMIT < TCVerdict.JUDGE_ERROR )
        self.assertFalse( TCVerdict.MEM_LIMIT < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.MEM_LIMIT < TCVerdict.ACCEPTED )
        self.assertFalse( TCVerdict.MEM_LIMIT < TCVerdict.MEM_LIMIT )
        self.assertTrue ( TCVerdict.MEM_LIMIT < TCVerdict.RUNTIME_ERROR )
        self.assertTrue ( TCVerdict.MEM_LIMIT < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.MEM_LIMIT < TCVerdict.JUDGE_ERROR )
        
        self.assertFalse( TCVerdict.RUNTIME_ERROR < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.RUNTIME_ERROR < TCVerdict.ACCEPTED )
        self.assertFalse( TCVerdict.RUNTIME_ERROR < TCVerdict.TIME_LIMIT )
        self.assertFalse( TCVerdict.RUNTIME_ERROR < TCVerdict.MEM_LIMIT )
        self.assertFalse( TCVerdict.RUNTIME_ERROR < TCVerdict.RUNTIME_ERROR )
        self.assertTrue ( TCVerdict.RUNTIME_ERROR < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.RUNTIME_ERROR < TCVerdict.JUDGE_ERROR )

        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.ACCEPTED )
        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.TIME_LIMIT )
        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.MEM_LIMIT )
        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.RUNTIME_ERROR )
        self.assertFalse( TCVerdict.WRONG_ANSWER < TCVerdict.WRONG_ANSWER )
        self.assertTrue ( TCVerdict.WRONG_ANSWER < TCVerdict.JUDGE_ERROR )
        
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.SKIPPED )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.ACCEPTED )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.TIME_LIMIT )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.MEM_LIMIT )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.RUNTIME_ERROR )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.WRONG_ANSWER )
        self.assertFalse( TCVerdict.JUDGE_ERROR < TCVerdict.JUDGE_ERROR )
    
    def test_verdict_to_submission_verdict (self):
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.ACCEPTED ),      SubmissionVerdict.ACCEPTED )
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.TIME_LIMIT ),    SubmissionVerdict.TIME_LIMIT )
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.MEM_LIMIT ),     SubmissionVerdict.MEM_LIMIT )
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.RUNTIME_ERROR ), SubmissionVerdict.RUNTIME_ERROR )
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.WRONG_ANSWER ),  SubmissionVerdict.WRONG_ANSWER )
        self.assertIs( SubmissionVerdict.fromTestVerdict( TCVerdict.JUDGE_ERROR ),   SubmissionVerdict.JUDGE_ERROR )

        with self.assertRaises(NotImplementedError):
            SubmissionVerdict.fromTestVerdict( TCVerdict.SKIPPED )
