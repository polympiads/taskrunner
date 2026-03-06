
"""
CCS Implementation of Teams, Persons and Accounts
"""

from typing import Literal, NotRequired, TypedDict

from ccs.models.contest import Contest
from django.contrib.auth.models import User

from ccs.models.managers.eventfeed import EventFeedKind, EventFeedManager
from ccs.models.visible import Visibility

class AccountCCSJson(TypedDict):
    id       : str
    username : str
    type     : "Literal['team', 'judge']"

class TeamCCSJson(TypedDict):
    id           : str
    name         : str
    display_name : NotRequired[str]

async def create_account_event (contest: Contest, id: str, username: str, type: "Literal['team', 'judge']"):
    payload : AccountCCSJson = {
        "id"       : id,
        "username" : username,
        "type"     : type
    }

    await EventFeedManager.acreate_event(
        contest,
        id,
        EventFeedKind.ACCOUNT,
        payload,
        Visibility.PUBLIC if type == "team" else Visibility.PRIVATE
    )
async def create_team_event (contest: Contest, id: str, name: str, display_name: "str | None" = None):
    payload: TeamCCSJson = {
        "id"   : id,
        "name" : name
    }
    if display_name is not None:
        payload["display_name"] = display_name

    await EventFeedManager.acreate_event(
        contest,
        id,
        EventFeedKind.TEAM,
        payload
    )

async def add_team_account_events (contest: Contest, user: User):
    await create_account_event(contest, str(user.pk), user.username, "team")
    await create_team_event(
        contest,
        str(user.pk),
        user.username,
        None if len(user.first_name) == 0 else user.first_name
    )
async def add_judge_account_events (contest: Contest, user: User):
    await create_account_event(contest, str(user.pk), user.username, "judge")
