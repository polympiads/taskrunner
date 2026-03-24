
from typing import TYPE_CHECKING, Literal, TypedDict

from ccs.models.eventfeed import EventFeed
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility

from asgiref.sync import async_to_sync

if TYPE_CHECKING:
    from balloons.models import Balloon

class BalloonCCSJson(TypedDict):
    id: str
    problem_id: str
    account_id: str
    status: "Literal['pending', 'taken', 'dropped']"

def ccs_json_from_ballon (balloon: "Balloon") -> BalloonCCSJson:
    from balloons.models import balloon_status_to_string
    return {
        "id": str(balloon.pk),
        "problem_id": str(balloon.problem.pk),
        "account_id": str(balloon.team.pk),
        "status": balloon_status_to_string(balloon.status)
    }

def create_ccs_for_balloons (balloon: "Balloon") -> EventFeed:
    return async_to_sync(EventFeedManager.acreate_event)(
        balloon.contest,
        str(balloon.pk),
        EventFeedKind.BALLOON,
        ccs_json_from_ballon(balloon),
        Visibility.PRIVATE
    )
