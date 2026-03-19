
import enum
import json
import channels.layers

from typing    import Any, Literal, TypedDict
from django.db import models
from django.contrib.auth.models import User

from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.visible import Visibility, visibility_to_string

class EventFeedKind (enum.Enum):
    CONTEST          = "contests"
    STATE            = "state"
    LANGUAGES        = "languages"
    JUDGEMENT_TYPES  = "judgement-types"
    SUBMISSION       = "submission"
    JUDGEMENT        = "judgements"
    CLARIFICATION    = "clarifications"

    PROBLEM = "problems"
    ACCOUNT = "accounts"
    TEAM    = "teams"

    # Non CCS compliant
    SUBMISSION_STATE = "submission-state"

class EventFeedMessage (TypedDict):
    type       : "Literal['event.feed']"
    contest_pk : int
    owner_pk   : "int | None"
    visibility : "Literal['public', 'private']"
    payload    : bytes
    event_id   : int

class EventFeedManager:
    @staticmethod
    async def afind_latest () -> int:
        values = await EventFeed.objects.aaggregate(models.Max('id'))
        lid = values['id__max']
        if lid is None:
            lid = -1
        return lid

    @staticmethod
    def get_feed_queryset (contest: Contest, user: User, upto: int, since: int | None = None):
        queryset = EventFeed.objects.filter(
            contest_id = contest.pk,
            pk__lte=upto
        )

        if since is not None:
            queryset = queryset.filter(pk__gt = since)

        if not user.is_superuser:
            queryset = queryset.filter(
                models.Q(visibility = Visibility.PUBLIC) |
                (
                    models.Q(owner_id = user.pk) &
                    models.Q(owner__isnull=False)
                )
            )
        
        return queryset
    
    @staticmethod
    async def acreate_event (
            contest: Contest,
            id:   str,
            type: EventFeedKind,
            data: Any,
            visibility: Visibility = Visibility.PUBLIC,
            owner: "User | None" = None
        ):
        raw_payload = { "id": id, "type": type.value, "data": data }
        raw_payload = json.dumps(raw_payload)

        event_feed = await EventFeed.objects.acreate(
            contest     = contest,
            owner       = owner,
            visibility  = visibility,
            raw_payload = raw_payload
        )

        layer = channels.layers.get_channel_layer()

        message: EventFeedMessage = {}
        message["type"]       = "event.feed"
        message["contest_pk"] = contest.pk
        message["owner_pk"]   = owner.pk if owner is not None else None
        message["visibility"] = visibility_to_string(visibility)
        message["payload"]    = event_feed.full_payload
        message["event_id"]   = event_feed.pk

        await layer.group_send(contest.eventfeed_group, message)

        return event_feed
