
from typing import Dict

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpRequest
from django.views import View
from django.db import transaction
from django.urls import reverse

from ccs.models.contest import MAX_CONTEST_NAME_LENGTH, Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import parse_visibility
from ccs.utils.responses import Json400
from ccs.utils.validators import validate_reltime, validate_reltime_nullable, validate_time_nullable
from ccs.utils.views import CollectionView, UpdateField

REV_CONTEST_LIST = "contest-list"
REV_CONTEST_ITEM = "contest-item"

def validate_name (name):
    if name is None:
        return None, "Field '{field}' shouldn't be empty."
    if not isinstance(name, str):
        return None, "Field '{field}' should be a string."
    if len(name) > MAX_CONTEST_NAME_LENGTH:
        return None, "Field '{field}' shouldn't have length bigger than " + str(MAX_CONTEST_NAME_LENGTH)
    return name, None
def validate_formal_name (formal_name):
    if formal_name is None:
        return formal_name, None
    return validate_name(formal_name)

@method_decorator(csrf_exempt, name='dispatch')
class ContestsView (CollectionView[Contest]):
    view_rule   = "contest.view"
    create_rule = "contest.create"

    async def display_json(self, item):
        return item.get_display_json()
    async def get_queryset(self, request, *args, **kwargs):
        return Contest.objects.all()
    
    def get_fields(self):
        return [
            UpdateField( "name",                       validator = validate_name ),
            UpdateField( "formal_name",                validator = validate_formal_name ),
            UpdateField( "start_time",                 validator = validate_time_nullable ),
            UpdateField( "countdown_pause_time",       validator = validate_reltime_nullable ),
            UpdateField( "duration",                   validator = validate_reltime ),
            UpdateField( "start_time",                 validator = validate_time_nullable ),
            UpdateField( "scoreboard_freeze_duration", validator = validate_reltime_nullable ),
            UpdateField( "scoreboard_thaw_time",       validator = validate_time_nullable ),
            UpdateField( "penalty_time",               validator = validate_reltime ),
            UpdateField( "visibility",                 validator = parse_visibility )
        ]
    async def create(self, updates: Dict, request, *args, **kwargs):
        if ('start_time' in updates) == ('countdown_pause_time' in updates):
            return Json400("There should be exactly one of the 'start_time' and 'countdown_pause_time' fields.")
        
        contest = await ContestManager.acreate_contest(**updates)

        return contest, reverse(REV_CONTEST_ITEM, kwargs = { 'pk': contest.pk })

@method_decorator(csrf_exempt, name='dispatch')
class ContestView (View):
    pass
