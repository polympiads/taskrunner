from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views import View

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from balloons.models import Balloon, balloon_status_from_string
from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.utils.responses import JsonResponseFailure

from asgiref.sync import sync_to_async

REV_BALLOON_SET_STATUS = "balloon-set-status"

@method_decorator(csrf_exempt, name='dispatch')
class SetBalloonStatusView (View):
    async def post (self, request: HttpRequest, pk: int, blpk: int):
        try:
            contest = await Contest.objects.aget(pk=pk)
        except Contest.DoesNotExist:
            return JsonResponseFailure(404, "Contest does not exist.")
        
        user = await request.auser()
        def can_view_contest ():
            return user.has_perm("contest.view", contest)
        
        if not await sync_to_async(can_view_contest)():
            return JsonResponseFailure(404, "Contest does not exist.")

        is_judge = False
        if user.is_authenticated:
            is_judge = await ContestAccount.objects.filter(
                contest = contest, user = user, role = ContestRole.JUDGE
            ).aexists()

        if not is_judge:
            return JsonResponseFailure(403, "Cannot modify balloon state.")

        try:
            balloon = await Balloon.objects.aget(contest = contest, pk = blpk)
        except Balloon.DoesNotExist:
            return JsonResponseFailure(404, "Balloon does not exist.")

        new_status_str = request.GET.get('status', None)
        if new_status_str is None:
            return JsonResponseFailure(400, "Field 'status' missing in url parameters.")

        new_status = balloon_status_from_string(new_status_str)
        if new_status is None:
            return JsonResponseFailure(400, f"Could not recognize status string '{new_status_str}'.")
        
        await sync_to_async(balloon.set_status)(new_status)
        return JsonResponse({}, status=200)
