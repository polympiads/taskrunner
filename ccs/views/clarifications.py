
import json

from django.http import HttpRequest, JsonResponse
from django.views import View

from ccs.feed.clarification import create_clarification_json
from ccs.models.contest import Contest
from ccs.models.managers.clarification import ClarificationManager
from ccs.utils.responses import Json400, Json403, JsonResponseFailure

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from asgiref.sync import sync_to_async

REV_CLARIFICATIONS = "clarifications"

@method_decorator(csrf_exempt, name='dispatch')
class ClarificationsView (View):
    async def post(self, request: HttpRequest, contest_id: int):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return Json400("Invalid JSON body.")

        text = body.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            return Json400("Field 'text' is required and must be a non-empty string.")

        reply_to   = body.get("reply_to", None)
        problem_id = body.get("problem_id", None)
        broadcast  = body.get("broadcast", False)

        if reply_to is not None and not isinstance(reply_to, int):
            return Json400("Field 'reply_to' must be an integer.")

        if problem_id is not None and not isinstance(problem_id, int):
            return Json400("Field 'problem_id' must be an integer.")

        if not isinstance(broadcast, bool):
            return Json400("Field 'broadcast' must be a boolean.")

        try:
            contest = await Contest.objects.aget(pk=contest_id)
        except Contest.DoesNotExist:
            return JsonResponseFailure(404, "Contest does not exist.")
        
        user = await request.auser()
        def can_view_contest ():
            return user.has_perm("contest.view", contest)
        
        if not await sync_to_async(can_view_contest)():
            return JsonResponseFailure(404, "Contest does not exist.")

        try:
            clarification, account = await sync_to_async(ClarificationManager.create_clarification)(
                contest    = contest,
                user       = user,
                text       = text.strip(),
                reply_to   = reply_to,
                problem_id = problem_id,
                broadcast  = broadcast
            )
        except ClarificationManager.ClarificationPermissionError as e:
            return Json403(str(e))
        except ClarificationManager.ClarificationDoesNotExistError as e:
            return JsonResponseFailure(404, str(e))

        return JsonResponse(create_clarification_json(contest, clarification, account), status=201)
