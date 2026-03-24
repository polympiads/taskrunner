
from django.contrib.auth.models import User

from ccs.feed.clarification import create_clarification_event
from ccs.models.clarification import Clarification
from ccs.models.contest import Contest, ContestAccount, ContestProblem, ContestRole

from django.utils import timezone

from problems.models.problem import Problem

class ClarificationManager:
    class ClarificationPermissionError (PermissionError):
        pass
    class ClarificationDoesNotExistError (ValueError):
        pass

    @staticmethod
    def create_clarification (
            contest : Contest,
            user    : User,
            
            text       : str,
            reply_to   : int | None,
            problem_id : int | None,
            broadcast  : bool
        ):
        if contest.started is None:
            raise ClarificationManager.ClarificationPermissionError("Can't send clarification before contest start.")
        
        try:
            account = ContestAccount.objects.get(contest = contest, user = user)
        except ContestAccount.DoesNotExist:
            raise ClarificationManager.ClarificationPermissionError("User is not registered in contest.")
        
        team_created  = user
        clarification = None
        if reply_to is not None:
            try:
                clarification = Clarification.objects.get(pk = reply_to)
            except Clarification.DoesNotExist:
                raise ClarificationManager.ClarificationDoesNotExistError("Cannot reply to clarification that doesn't exist.")
            
            if clarification.team.pk != user.pk and account.role != ContestRole.JUDGE:
                raise ClarificationManager.ClarificationDoesNotExistError("Cannot reply to clarification that doesn't exist.")

            if clarification.broadcast and not broadcast:
                raise ClarificationManager.ClarificationPermissionError("Cannot reply to broadcasted clarification in non-broadcast mode.")

            team_created = clarification.team
        
        if clarification is not None:
            old_problem    = clarification.problem
            old_problem_id = None if old_problem is None else old_problem.pk

            if old_problem_id != problem_id:
                raise ClarificationManager.ClarificationPermissionError("Problem of reply should be the same as the original.")

        problem: "Problem | None" = None
        if problem_id is not None:
            try:
                problem = Problem.objects.get(pk = problem_id)
            except Problem.DoesNotExist:
                raise ClarificationManager.ClarificationDoesNotExistError("Problem does not exist.")

            try:
                ContestProblem.objects.get(contest = contest, problem = problem)
            except ContestProblem.DoesNotExist:
                raise ClarificationManager.ClarificationDoesNotExistError("Problem does not exist on that contest.")

        if broadcast and account.role != ContestRole.JUDGE:
            raise ClarificationManager.ClarificationPermissionError("Only judges can broadcast a clarification.")

        clarification = Clarification.objects.create(
            contest = contest,
            author  = user,
            team    = team_created,

            reply_to = clarification,

            content   = text,
            time      = timezone.now(),
            broadcast = broadcast,

            problem = problem
        )

        create_clarification_event(contest, clarification, account)

        return clarification, account
