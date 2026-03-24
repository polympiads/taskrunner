
from typing import Literal

from django.conf import settings
from django.http import FileResponse, HttpRequest
from django.views import View

from ccs.models.contest import Contest, ContestAccount, ContestRole
from ccs.utils.responses import JsonResponseFailure

from asgiref.sync import sync_to_async

from printing.models import ContestPrint

REV_PRINT_DOWNLOAD = "print-download"

CODE_KIND = "code"
PDF_KIND  = "pdf"
ERR_KIND  = "err"

class InfoKind:
    location        : "str | None"
    should_be_judge : bool

    def __init__ (self, location: "str | None", should_be_judge: bool):
        self.location = location
        self.should_be_judge = should_be_judge

class PrintDownloadView (View):
    def get_info_from_kind (self, print: ContestPrint, kind: "Literal['code', 'pdf', 'err']") -> InfoKind:
        match kind:
            case "code" : return InfoKind(print.code_location, False)
            case "pdf"  : return InfoKind(print.pdf_location,  False)
            case "err"  : return InfoKind(print.err_location,  True)
        
        return None

    async def get (self, request: HttpRequest, pk: int, prpk: int, kind: "Literal['code', 'pdf', 'err']"):
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
                .select_related("owner") \
                .aget(contest = contest, pk = prpk)
        except ContestPrint.DoesNotExist:
            return JsonResponseFailure(404, "Print Object does not exist.")

        is_owner = user.pk == print.owner.pk
        is_judge = False
        if user.is_authenticated:
            is_judge = await ContestAccount.objects.filter(
                contest = contest, user = user, role = ContestRole.JUDGE).aexists()

        info_kind = self.get_info_from_kind(print, kind)
        if info_kind is None:
            return JsonResponseFailure(401, "Invalid Print Kind.")

        if not (is_judge or (is_owner and not info_kind.should_be_judge)) or info_kind.location is None:
            return JsonResponseFailure(404, "Print Object does not exist.")
        
        file_target = await settings.STORAGE_CLIENT.download(info_kind.location)

        return FileResponse(
            open(file_target, "rb"),
            as_attachment = False
        )
