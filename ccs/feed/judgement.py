

from typing import TypedDict

from ccs.feed.judgetype import JudgementType
from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager

from asgiref.sync import async_to_sync

from ccs.models.visible import Visibility
from submit.models.verdict import SubmissionVerdict

class JudgementCCSJson (TypedDict):
    id                : str
    submission_id     : str
    judgement_type_id : str

def create_judgement_event_params (
        contest: Contest,
        submission_id: int,
        judgement_type: JudgementType
    ):
    from submit.models.submission import Submission
    submission = Submission.objects.get(pk = submission_id)
    contest_account: ContestAccount = ContestAccount.objects.get(contest = contest, user = submission.user)

    submission_id = str(submission_id)

    judgement: JudgementCCSJson = {
        "id": submission_id,
        "submission_id": submission_id,
        "judgement_type_id": judgement_type.value
    }

    return (
        contest,
        submission_id,
        EventFeedKind.JUDGEMENT,
        judgement,
        (Visibility.PUBLIC if contest_account.role == ContestRole.TEAM else Visibility.PRIVATE),
        submission.user
    )
def create_judgement_event (
        contest: "Contest",
        submission_id: int,
        verdict: SubmissionVerdict
    ):
    return async_to_sync(
        EventFeedManager.acreate_event
    )(*create_judgement_event_params(contest, submission_id, JudgementType.from_verdict(verdict)))
