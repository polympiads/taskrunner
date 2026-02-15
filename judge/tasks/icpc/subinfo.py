
from typing import TypedDict
from judge.languages import LanguageKind

class s_SubmissionInformation (TypedDict):
    submission_id    : int
    problem_location : str
    exec_location    : str

    language : str
class SubmissionInformation:
    submission_id    : int
    problem_location : str
    exec_location    : str

    language : LanguageKind

    def __init__ (self, submission_id: int, problem_location: str, exec_location: str, language: LanguageKind):
        self.submission_id = submission_id
        self.problem_location = problem_location
        self.exec_location = exec_location
        self.language = language
    def serialize (self) -> s_SubmissionInformation:
        return {
            "submission_id": self.submission_id,
            "problem_location": self.problem_location,
            "exec_location": self.exec_location,
            "language": self.language.value}
    @staticmethod
    def deserialize (sub: s_SubmissionInformation) -> "SubmissionInformation":
        return SubmissionInformation(
            sub["submission_id"],
            sub["problem_location"],
            sub["exec_location"],
            LanguageKind(sub["language"])
        )
