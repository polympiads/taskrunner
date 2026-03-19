
from typing import TypedDict

from ccs.models.clarification import Clarification
from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility
from ccs.utils.time import Reltime, Time

from asgiref.sync import async_to_sync

class ClarificationCCSJson (TypedDict):
    id           : str
    from_team_id : str | None
    reply_to_id  : str | None
    problem_id   : str | None
    text         : str
    time         : str
    contest_time : str
    broadcast    : bool

def create_clarification_json (
        contest: Contest,
        clarification: Clarification,
        author: ContestAccount
    ) -> ClarificationCCSJson:
    return {
        "id": str(clarification.pk),
        "from_team_id" : None if author.role == ContestRole.JUDGE else str(author.user.pk),
        "reply_to_id"  : str(clarification.reply_to.pk) if clarification.reply_to is not None else None,
        "problem_id"   : str(clarification.problem.pk)  if clarification.problem  is not None else None,
        "text"         : clarification.content,
        "time"         : Time.string_from_time(clarification.time),
        "contest_time" : Reltime.string_from_reltime(clarification.time - contest.started),
        "broadcast"    : clarification.broadcast
    }

def create_clarification_event (
        contest: Contest,
        clarification: Clarification,
        author: ContestAccount
    ):
    json = create_clarification_json(contest, clarification, author)

    visibility = Visibility.PRIVATE
    owner = clarification.team

    if clarification.broadcast:
        visibility = Visibility.PUBLIC

    return async_to_sync( EventFeedManager.acreate_event )(
        contest,
        str(clarification.pk),
        EventFeedKind.CLARIFICATION,
        json,
        visibility=visibility,
        owner=owner
    )
