
import asyncio
import datetime
from typing import TypedDict

from asgiref.sync import async_to_sync
from django.db import transaction
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django_enumfield import enum
import rules
from rules.predicates import is_staff, is_superuser

from ccs.models.visible import Visibility, is_public
from ccs.utils.time import Reltime, Time

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

MAX_CONTEST_NAME_LENGTH = 64

class ContestManager (models.Manager):
    @staticmethod
    async def acreate_contest (**updates):
        from ccs.models.eventfeed import EventFeed, EventFeedKind

        contest = await Contest.objects.acreate(**updates)

        await EventFeed.objects.acreate_event(
            contest,
            "contest",
            EventFeedKind.CONTEST,
            contest.get_display_json()
        )

        return contest

    @staticmethod
    def start_contest (contest_id: int):
        from ccs.models.eventfeed import EventFeed, EventFeedKind
        from ccs.views.languages import LanguagesCCSJson
        from ccs.views.judgetype import JudgementTypesCCSJson

        with transaction.atomic():
            contest = Contest.objects.select_for_update().get(pk = contest_id)
            if contest.started is not None:
                raise ValueError("Can't start contest that has started.")
            
            contest.started = timezone.now()
            contest.save()
        
            async def send_events ():
                await EventFeed.objects.acreate_event(
                    contest,
                    "contest-start",
                    EventFeedKind.STATE,
                    contest.get_json_state()
                )

                await LanguagesCCSJson.acreate_languages_events(contest)
                await JudgementTypesCCSJson.acreate_judgement_types(contest)
            
            async_to_sync(send_events)()

class Contest (models.Model):
    objects : "models.Manager[Contest] | ContestManager" = ContestManager()

    visibility = enum.EnumField(Visibility)

    name        = models.CharField(max_length=MAX_CONTEST_NAME_LENGTH)
    formal_name = models.CharField(max_length=MAX_CONTEST_NAME_LENGTH, default = None, null = True)

    start_time           = models.DateTimeField(default = None, null = True)
    countdown_pause_time = models.DurationField(default = None, null = True)

    duration = models.DurationField()

    scoreboard_freeze_duration = models.DurationField(
        default = datetime.timedelta(), null = True )
    scoreboard_thaw_time = models.DateTimeField(
        default = None, null = True )

    penalty_time = models.DurationField()

    # Contest State
    started        = models.DateTimeField(default = None, null = True)
    frozen         = models.DateTimeField(default = None, null = True)
    ended          = models.DateTimeField(default = None, null = True)
    thawed         = models.DateTimeField(default = None, null = True)
    finalized      = models.DateTimeField(default = None, null = True)
    end_of_updates = models.DateTimeField(default = None, null = True)
    
    @property
    def eventfeed_group (self):
        return "contest_eventfeed__" + str(self.pk)

    def get_name (self) -> str:
        return self.name
    def get_formal_name (self) -> str:
        if self.formal_name is not None:
            return self.formal_name
        return self.get_name()
    
    def get_start_time (self) -> "datetime.datetime | None":
        return self.start_time
    def get_countdown_pause_time (self) -> "datetime.timedelta | None":
        return self.countdown_pause_time
    def get_duration (self) -> "datetime.timedelta":
        return self.duration
    def get_scoreboard_freeze_duration (self) -> "datetime.timedelta":
        return self.scoreboard_freeze_duration
    def get_scoreboard_thaw_time (self) -> "datetime.datetime | None":
        return self.scoreboard_thaw_time
    def get_penalty_time (self) -> "datetime.timedelta":
        return self.penalty_time

    def get_scoreboard_type (self) -> str:
        return "pass-fail" # the judge currently does not support "score" scoreboard type

    def get_json_state (self) -> ContestStateCCSJson:
        result: ContestStateCCSJson = {}
        def put_field (field: str, content: "datetime.datetime | None"):
            if content is None:
                result[field] = None
            else:
                result[field] = Time.string_from_time(content)
        
        put_field("started",        self.started)
        put_field("frozen",         self.frozen)
        put_field("ended",          self.ended)
        put_field("thawed",         self.thawed)
        put_field("finalized",      self.finalized)
        put_field("end_of_updates", self.end_of_updates)

        return result
    def get_display_json (self) -> ContestCCSJson:
        result: ContestCCSJson = {}
        def put_into (label: str, value, id = lambda x : x):
            if value is None:
                return
            result[label] = id(value)

        put_into("id",                         self.pk,                               str                        )
        put_into("name",                       self.get_name()                                                   )
        put_into("formal_name",                self.get_formal_name()                                            )
        put_into("start_time",                 self.get_start_time(),                 Time.string_from_time      )
        put_into("countdown_pause_time",       self.get_countdown_pause_time(),       Reltime.string_from_reltime)
        put_into("duration",                   self.get_duration(),                   Reltime.string_from_reltime)
        put_into("scoreboard_freeze_duration", self.get_scoreboard_freeze_duration(), Reltime.string_from_reltime)
        put_into("scoreboard_thaw_time",       self.get_scoreboard_thaw_time(),       Time.string_from_time      )
        put_into("scoreboard_type",            self.get_scoreboard_type()                                        )
        put_into("penalty_time",               self.get_penalty_time(),               Reltime.string_from_reltime)
        
        return result

@rules.predicate
def is_contest_visible (user: User, contest: Contest):
    return is_public(user, contest.visibility) | is_staff(user)

rules.add_perm("contest.view",   is_contest_visible)
rules.add_perm("contest.create", is_superuser)
rules.add_perm("contest.edit",   is_superuser)
rules.add_perm("contest.delete", is_superuser)
