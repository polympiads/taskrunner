
class SubmissionInformation:
    submission_id    : int
    problem_location : str
    exec_location    : str

    def __init__ (self, submission_id: int, problem_location: str, exec_location: str):
        self.submission_id = submission_id
        self.problem_location = problem_location
        self.exec_location = exec_location
