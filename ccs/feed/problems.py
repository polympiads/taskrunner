
from typing import List, Literal, TypedDict

from ccs.models.contest import Contest
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility
from django.urls import reverse

from ccs.views.problem import REV_STATEMENT

class StatementCCSJson (TypedDict):
    href : str
    mime : "Literal['application/pdf']"

class ProblemsCCSJson (TypedDict):
    id    : str
    label : str
    name  : str

    time_limit   : float
    memory_limit : int

    statement : "List[StatementCCSJson]"

def create_problem_event_payload (
        id    : int,
        label : str,
        name  : str,
        
        time_limit_seconds  : float,
        memory_limit_mbytes : int,
        
        statement: str
    ) -> ProblemsCCSJson:
    return {
        "id": str(id),
        "label": label,
        "name": name,
        "statement": [
            {
                "mime": "application/pdf",
                "href": statement
            }
        ],
        "time_limit": time_limit_seconds,
        "memory_limit": memory_limit_mbytes
    }

async def create_problem_event (
        contest: Contest,

        id    : int,
        label : str,
        name  : str,
        
        time_limit_seconds  : float,
        memory_limit_mbytes : int
    ):
    await EventFeedManager.acreate_event(
        contest,
        str(id),
        EventFeedKind.PROBLEM,
        create_problem_event_payload(
            id,
            label,
            name,

            time_limit_seconds,
            memory_limit_mbytes,
            
            reverse(REV_STATEMENT, kwargs = { "pk": contest.pk, "pbpk": id }, urlconf="ccs.urls")
        ),
        Visibility.PUBLIC
    )
