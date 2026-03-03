

from typing import TypedDict

from ccs.feed.judgetype import JudgementType
from ccs.models.contest import Contest
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager

from asgiref.sync import async_to_sync

class JudgementCCSJson (TypedDict):
    id                : str
    submission_id     : str
    judgement_type_id : str

def create_judgement_event_params (
        contest: Contest,
        submission_id: int,
        judgement_type: JudgementType
    ):
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
        judgement
    )
def create_judgement_event (
        contest: "Contest",
        submission_id: int,
        judgement_type: JudgementType
    ):
    return async_to_sync(
        EventFeedManager.acreate_event(*create_judgement_event_params(contest, submission_id, judgement_type))
    )
