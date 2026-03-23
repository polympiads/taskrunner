
from django.http import FileResponse, HttpRequest
from django.views import View

from ccs.models.contest import Contest, ContestAccount, ContestProblem, ContestRole
from ccs.utils.responses import JsonResponseFailure

from asgiref.sync import sync_to_async

from problems.models.problem import Problem
from storecli.problems.storage import ProblemStorage

REV_STATEMENT = "problem-statement"

class StatementView (View):
    async def get (self, request: HttpRequest, pk: int, pbpk: int):
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
        
        if contest.started is None and not is_judge:
            return JsonResponseFailure(403, "Contest hasn't started yet.")
        
        try:
            problem = await Problem.objects.aget(pk=pbpk)

            contest_problem = await ContestProblem.objects.aget(problem = problem, contest = contest)
        except Problem.DoesNotExist:
            return JsonResponseFailure(404, "Problem does not exist.")
        except ContestProblem.DoesNotExist:
            return JsonResponseFailure(404, "Problem does not exist.")

        if problem.problem_location is None:
            return JsonResponseFailure(500, "Problem isn't prepared.")

        storage   = await ProblemStorage.download(problem.problem_location)
        statement = storage.get_statement()

        return FileResponse(
            open(statement, "rb"),
            content_type  = "application/pdf",
            as_attachment = False
        )
