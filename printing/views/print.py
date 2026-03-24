
import os
import tempfile

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views import View
from django.core.files.uploadedfile import UploadedFile

from ccs.models.contest import Contest, ContestAccount
from ccs.utils.responses import JsonResponseFailure

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from asgiref.sync import sync_to_async

from printing.ccs import ccs_json_from_print
from printing.models import ContestPrint

REV_PRINT_CREATE = "print-create"

@method_decorator(csrf_exempt, name='dispatch')
class CreatePrintView (View):
    async def post (self, request: HttpRequest, pk: str):
        try:
            contest = await Contest.objects.aget(pk=pk)
        except Contest.DoesNotExist:
            return JsonResponseFailure(404, "Contest does not exist.")
        
        user = await request.auser()
        def can_view_contest ():
            return user.has_perm("contest.view", contest)
        
        if not await sync_to_async(can_view_contest)():
            return JsonResponseFailure(404, "Contest does not exist.")

        is_participant = False
        if user.is_authenticated:
            is_participant = await ContestAccount.objects.filter(
                contest = contest, user = user
            ).aexists()
        
        if not is_participant:
            return JsonResponseFailure(403, "Cannot print for that contest.")

        def write_to_tmpfile (uploaded_file: "UploadedFile", tmpfile: "tempfile._TemporaryFileWrapper[str]"):
            for chunk in uploaded_file.chunks():
                tmpfile.write(chunk)
            tmpfile.flush()
        
        uploaded_file = request.FILES.get("file", None)
        if uploaded_file is None:
            return JsonResponseFailure(400, f"Could not find file 'file' in POST request.")
        
        if uploaded_file.size > settings.MAX_PRINT_SIZE:
            return JsonResponseFailure(400, f"Submitted file is too large.")

        with tempfile.NamedTemporaryFile("wb", delete = False) as tmpfile:
            filename = tmpfile.name
            await sync_to_async(write_to_tmpfile)(uploaded_file, tmpfile)
            tmpfile.close()

            with open(filename, "rb") as file:
                lines = file.readlines()
                
                if len(lines) > settings.MAX_PRINT_LINE_COUNT:
                    return JsonResponseFailure(400, f"Submitted file has too many lines.")

                for line in lines:
                    words = line.split()
                    for word in words:
                        if len(word) > settings.MAX_PRINT_WORD_SIZE:
                            return JsonResponseFailure(400, f"Submitted file has a word too long.")

            code_location = settings.STORAGE_CLIENT.reserve()
            await settings.STORAGE_CLIENT.upload(filename, code_location)

            if os.path.exists(filename):
                os.remove(filename)

        code_print = await sync_to_async(ContestPrint.objects.create_print)(
            contest,
            user,
            code_location
        )
        
        return JsonResponse(await sync_to_async(ccs_json_from_print)(code_print), status = 201)
