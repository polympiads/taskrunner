
from typing import TYPE_CHECKING

from django.db import models, transaction
from django_enumfield import enum

if TYPE_CHECKING:
    from ccs.models.contest import Contest

class ProblemManager (models.Manager):
    @staticmethod
    def create_from_storage (storage: str):
        return Problem.objects.create(problem_location = storage)
    @staticmethod
    def create_from_polygon (pkg_storage: str):
        problem = Problem.objects.create(problem_location = None)

        from problems.models.preparation import Preparation
        Preparation.objects.create_polygon_preparation(problem, pkg_storage)

        return problem
    @staticmethod
    def create_from_polygon_for_contest (pkg_storage: str, contest: "Contest", label: str):
        problem = Problem.objects.create(problem_location = None)

        from ccs.models.contest import ContestProblem
        ContestProblem.objects.create(
            problem = problem,
            contest = contest,
            label   = label
        )

        from problems.models.preparation import Preparation
        Preparation.objects.create_polygon_preparation(problem, pkg_storage)

        return problem

    @staticmethod
    def set_problem_location (problem_id: int, problem_location: str):
        with transaction.atomic():
            rows_updated = Problem.objects \
                .filter(pk = problem_id) \
                .update(problem_location = problem_location)
            
            if rows_updated == 0:
                raise Problem.DoesNotExist(
                    f"Could not set problem location for pk={problem_id}")

        # TODO notify channel of change

class Problem (models.Model):
    # By default, a problem that hasn't been imported is None
    problem_location = models.TextField( null=True, default=None )

    objects: "ProblemManager | models.Manager[Problem]" = ProblemManager()
