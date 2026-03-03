
from django_enumfield import enum

class SubmissionStatus (enum.Enum):
    STARTING  = 0
    COMPILING = 1
    RUNNING   = 2
    FINISHED  = 3
    FAILED    = 4

def submission_status_to_string (status: SubmissionStatus):
    match status:
        case SubmissionStatus.STARTING:  return "starting"
        case SubmissionStatus.COMPILING: return "compiling"
        case SubmissionStatus.RUNNING:   return "running"
        case SubmissionStatus.FINISHED:  return "finished"
        case SubmissionStatus.FAILED:    return "failed"
        
    raise NotImplementedError(f"Could not recognize submission status '{status}'")
