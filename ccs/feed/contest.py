
from typing import TYPE_CHECKING, TypedDict

from ccs.models.managers.eventfeed import EventFeedManager, EventFeedKind


if TYPE_CHECKING:
    from ccs.models.contest import Contest


class ContestCCSJson (TypedDict):
    id          : str # string for the given int pk
    name        : str
    formal_name : str
    
    start_time             : str
    countdown_pause_time   : str
    duration               : str
    scoreboard_freeze_time : str
    scoreboard_thaw_time   : str
    scoreboard_type        : str

    penalty_time : str
class ContestStateCCSJson (TypedDict):
    started        : "str | None"
    ended          : "str | None"
    frozen         : "str | None"
    thawed         : "str | None"
    finalized      : "str | None"
    end_of_updates : "str | None"

def create_contest_event_params (contest: "Contest"):
    return (
        contest,
        "contest",
        EventFeedKind.CONTEST,
        contest.get_display_json()
    )
async def acreate_contest_event (contest: "Contest"):
    return await EventFeedManager.acreate_event(*create_contest_event_params(contest))

def create_contest_state_event_params (contest: "Contest", kind: str):
    return (
        contest,
        kind,
        EventFeedKind.STATE,
        contest.get_json_state()
    )
def create_contest_start_event_params (contest: "Contest"):
    return create_contest_state_event_params(contest, "contest-start")

async def acreate_contest_start_event (contest: "Contest"):
    return await EventFeedManager.acreate_event(*create_contest_start_event_params(contest))
