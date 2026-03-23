
from django.http import HttpRequest, JsonResponse
from django.views import View

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from asgiref.sync import sync_to_async

from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.utils.responses import JsonResponseFailure
from printing.ccs import ccs_json_from_print
from printing.models import ContestPrint, PrintStatus

REV_PRINT_DONE = "print-done"

@method_decorator(csrf_exempt, name='dispatch')
class PrintDoneView (View):
    async def post (self, request: HttpRequest, pk: int, prpk: int):
        try:
            contest = await Contest.objects.aget(pk=pk)
        except Contest.DoesNotExist:
            return JsonResponseFailure(404, "Contest does not exist.")
        
        user = await request.auser()
        def can_view_contest ():
            return user.has_perm("contest.view", contest)
        
        if not await sync_to_async(can_view_contest)():
            return JsonResponseFailure(404, "Contest does not exist.")

        try:
            print = await ContestPrint.objects \
                .aget(contest = contest, pk = prpk)
        except ContestPrint.DoesNotExist:
            return JsonResponseFailure(404, "Print Object does not exist.")

        is_judge = False
        if user.is_authenticated:
            is_judge = await ContestAccount.objects.filter(
                contest = contest, user = user, role = ContestRole.JUDGE).aexists()

        if not is_judge:
            return JsonResponseFailure(403, "Cannot modify Print Object.")

        if print.status != PrintStatus.READY:
            return JsonResponseFailure(401, "Cannot make print DONE if it isn't READY.")
        
        await sync_to_async(print.on_done)()
        return JsonResponse(await sync_to_async(ccs_json_from_print)(print), status = 200)
