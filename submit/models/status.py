
from django_enumfield import enum

class SubmissionStatus (enum.Enum):
    STARTING  = 0
    COMPILING = 1
    RUNNING   = 2
    FINISHED  = 3
    FAILED    = 4
