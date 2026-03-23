
import os
import tempfile

from django.conf import settings
from django.http import FileResponse, HttpRequest, JsonResponse
from django.core.files.uploadedfile import UploadedFile
from django.views import View

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from ccs.feed.submission import create_submission_event_params
from ccs.models.contest import Contest, ContestAccount, ContestProblem, ContestRole
from ccs.utils.responses import JsonResponseFailure

from asgiref.sync import sync_to_async

from judge.languages import LanguageKind, get_language
from problems.models.problem import Problem
from submit.models.submission import Submission, SubmitError

REV_VIEW_CODE = "submissions-code"
REV_SUBMIT = "submit"

class SubmissionCodeView (View):
    async def get (self, request: HttpRequest, pk: str, subpk: str):
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
            submission = await Submission.objects.select_related("user").aget(
                contest = contest,
                pk = subpk
            )
        except Submission.DoesNotExist:
            return JsonResponseFailure(404, "Submission does not exist.")

        is_judge = False
        if user.is_authenticated:
            is_judge = await ContestAccount.objects.filter(
                contest = contest, user = user, role = ContestRole.JUDGE).aexists()

        if submission.user != user and not user.is_staff and not is_judge:
            return JsonResponseFailure(404, "Submission does not exist.")
        
        code_file = await settings.STORAGE_CLIENT.download(submission.code_location)

        return FileResponse(
            open(code_file, "rb"),
            as_attachment = False
        )

@method_decorator(csrf_exempt, name='dispatch')
class SubmitView (View):
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
        
        problem_id = request.GET.get('problem_id', None)
        if problem_id is None:
            return JsonResponseFailure(400, "Missing field 'problem_id' in URL parameters.")

        try:
            problem = await Problem.objects.aget(pk = problem_id)
            
            contest_problem = await ContestProblem.objects.aget(problem = problem, contest = contest)
        except Problem.DoesNotExist:
            return JsonResponseFailure(404, "Problem does not exist.")
        except ContestProblem.DoesNotExist:
            return JsonResponseFailure(404, "Problem does not exist.")
        
        if problem.problem_location is None:
            return JsonResponseFailure(500, "Problem isn't prepared.")

        language_id = request.GET.get('language_id', None)
        if language_id is None:
            return JsonResponseFailure(400, "Missing field 'language_id' in URL parameters.")
        
        language_kind = None
        for pot_language_kind in LanguageKind:
            pot_language = get_language(pot_language_kind)

            if pot_language.ccs_language_information["id"] == language_id:
                language_kind = pot_language_kind
                break

        if language_kind is None:
            return JsonResponseFailure(400, f"Could not recognize language id '{language_id}'.")

        def write_to_tmpfile (uploaded_file: "UploadedFile", tmpfile: "tempfile._TemporaryFileWrapper[str]"):
            for chunk in uploaded_file.chunks():
                tmpfile.write(chunk)
            tmpfile.flush()
        
        uploaded_file = request.FILES.get("file", None)
        if uploaded_file is None:
            return JsonResponseFailure(400, f"Could not find file 'file' in POST request.")
        if uploaded_file.size > settings.MAX_SUBMISSION_SIZE:
            return JsonResponseFailure(400, f"Submitted file is too large.")

        language = get_language(language_kind)
        with tempfile.NamedTemporaryFile("wb", suffix = language.extension, delete = False) as tmpfile:
            filename = tmpfile.name
            await sync_to_async(write_to_tmpfile)(uploaded_file, tmpfile)
            tmpfile.close()

            code_location = settings.STORAGE_CLIENT.reserve()
            await settings.STORAGE_CLIENT.upload(filename, code_location)

            if os.path.exists(filename):
                os.remove(filename)

        try:
            submission = await sync_to_async(Submission.objects.create_submission)(
                user,
                problem,
                code_location,
                language_kind,
                contest
            )
        except SubmitError as error:
            return JsonResponseFailure(403, str(error))

        submission_ccs = (await sync_to_async(create_submission_event_params)(contest, submission.pk, language_kind, problem_id, user))[3]
        return JsonResponse(submission_ccs, status = 201)
