
from django_enumfield import enum

class TestCaseVerdict (enum.Enum):
    SKIPPED       = -1
    ACCEPTED      = 0
    TIME_LIMIT    = 1
    MEM_LIMIT     = 2
    RUNTIME_ERROR = 3
    WRONG_ANSWER  = 4
    JUDGE_ERROR   = 5

    def single_char_representation (self):
        match self:
            case TestCaseVerdict.SKIPPED: return 'S'
            case TestCaseVerdict.ACCEPTED: return 'A'
            case TestCaseVerdict.TIME_LIMIT: return 'T'
            case TestCaseVerdict.MEM_LIMIT: return 'M'
            case TestCaseVerdict.RUNTIME_ERROR: return 'R'
            case TestCaseVerdict.WRONG_ANSWER: return 'W'
            case TestCaseVerdict.JUDGE_ERROR: return 'J'
        
        raise NotImplementedError(f"Test case verdict {self} has no single character representation")
            
    def __lt__ (self, other: "TestCaseVerdict"):
        return self.value < other.value

class SubmissionVerdict (enum.Enum):
    PENDING        = -1
    ACCEPTED       = 0
    TIME_LIMIT     = 1
    MEM_LIMIT      = 2
    RUNTIME_ERROR  = 3
    WRONG_ANSWER   = 4
    COMPILER_ERROR = 5
    JUDGE_ERROR    = 6

    @staticmethod
    def fromTestVerdict (verdict : TestCaseVerdict) -> "SubmissionVerdict":
        match verdict:
            case TestCaseVerdict.ACCEPTED:      return SubmissionVerdict.ACCEPTED
            case TestCaseVerdict.TIME_LIMIT:    return SubmissionVerdict.TIME_LIMIT
            case TestCaseVerdict.MEM_LIMIT:     return SubmissionVerdict.MEM_LIMIT
            case TestCaseVerdict.RUNTIME_ERROR: return SubmissionVerdict.RUNTIME_ERROR
            case TestCaseVerdict.WRONG_ANSWER:  return SubmissionVerdict.WRONG_ANSWER
            case TestCaseVerdict.JUDGE_ERROR:   return SubmissionVerdict.JUDGE_ERROR
        
        raise NotImplementedError(f"Test verdict {verdict} does not have a submission verdict")
