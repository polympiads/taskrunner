
from judge.languages import LanguageKind


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
