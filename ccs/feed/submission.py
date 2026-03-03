
from typing import Literal, NotRequired, TypedDict

from django.contrib.auth.models import User

from ccs.models.contest import Contest
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility
from judge.languages import LanguageKind, get_language

from asgiref.sync import async_to_sync

from submit.models.status import SubmissionStatus, submission_status_to_string

class SubmissionCCSJson (TypedDict):
    id : str

    language_id : str
    problem_id  : str

    team_id    : NotRequired[str]
    account_id : NotRequired[str]

class SubmissionStateCCSJson (TypedDict):
    submission_id : str
    status : "Literal['starting', 'compiling', 'running', 'finished', 'failed']"

def create_submission_event_params (
        contest: Contest,
        id : int,

        language   : LanguageKind,
        problem_id : int,

        account: User
    ):
    # TODO determine if account is a team member
    submission_id = str(id)

    ccs_json : SubmissionCCSJson = {
        "id": submission_id,
        "language_id": get_language(language).ccs_language_information["id"],
        "problem_id": problem_id,

        "account_id": str(account.pk)
    }
    return (
        contest,
        submission_id,
        EventFeedKind.STATE,
        ccs_json
    ) # TODO determine if it should be PRIVATE / PUBLIC
def create_contest_start_event (
        contest: "Contest",
        
        id : int,

        language   : LanguageKind,
        problem_id : int,

        account: User
    ):
    return async_to_sync(
        EventFeedManager.acreate_event(*create_submission_event_params(contest, id, language, problem_id, account))
    )

def create_submission_state_params (
        contest : Contest,

        submission_id    : int,
        submission_state : SubmissionStatus,
        
        account : User
    ):
    submission_id = str(submission_id)
    ccs_json : SubmissionStateCCSJson = {
        "submission_id" : submission_id,
        "status" : submission_status_to_string(submission_state)
    }
    return (
        contest,
        submission_id,
        EventFeedKind.SUBMISSION_STATE,
        ccs_json,
        Visibility.PRIVATE, # TODO determine if it truely should be private (e.g. frozen etc...)
        account
    )

def create_contest_state_event (
        contest: "Contest",
        
        submission_id    : int,
        submission_state : SubmissionStatus,
        
        account : User
    ):
    return async_to_sync(
        EventFeedManager.acreate_event(*create_submission_state_params(contest, submission_id, submission_state, account))
    )