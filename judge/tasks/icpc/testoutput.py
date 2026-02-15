
from typing import List, TypedDict
from submit.models.verdict import TestCaseVerdict

class s_TestCaseOutput (TypedDict):
    test_id: int
    verdict: str

class TestCaseOutput:
    test_id: int
    verdict: TestCaseVerdict

    def __lt__ (self, other: "TestCaseOutput"):
        return self.test_id < other.test_id

    def __str__ (self):
        return f"({self.test_id}: {self.verdict.name})"
    def __init__ (self, test_id: int, verdict: TestCaseVerdict):
        self.test_id = test_id
        self.verdict = verdict

type TestCasesOutput   = "List[TestCasesOutput] | TestCaseOutput"
type s_TestCasesOutput = "List[s_TestCasesOutput] | s_TestCaseOutput"

def serialize_outputs (test_cases: TestCasesOutput) -> s_TestCasesOutput:
    if isinstance(test_cases, list):
        return list(map(serialize_outputs, test_cases))
    return { "test_id": test_cases.test_id, "verdict": test_cases.verdict.value }
def deserialize_outputs (test_cases: s_TestCasesOutput) -> TestCasesOutput:
    if isinstance(test_cases, list):
        return list(map(deserialize_outputs, test_cases))
    return TestCaseOutput(test_cases["test_id"], TestCaseVerdict(test_cases["verdict"]))

def flatten_test_cases_output (test_cases : List[TestCasesOutput]) -> List[TestCaseOutput]:
    result: List[TestCaseOutput] = []
    def helper_flatten (test_case: TestCasesOutput):
        if isinstance(test_case, list):
            for subtest in test_case:
                helper_flatten(subtest)
        else:
            result.append(test_case)

    for test in test_cases:
        helper_flatten(test)
    return result

def get_test_cases_verdict (test_cases: TestCasesOutput) -> TestCaseVerdict:
    if isinstance(test_cases, list):
        return max(TestCaseVerdict.ACCEPTED, TestCaseVerdict.ACCEPTED, *list(map(get_test_cases_verdict, test_cases)))
    return test_cases.verdict

def as_string_buffer (test_cases: List[TestCaseOutput]) -> str:
    buffer = []
    for test_case in test_cases:
        buffer.append( TestCaseVerdict.single_char_representation( test_case.verdict ) )
    return "".join(buffer)
