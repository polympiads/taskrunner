
import asyncio
from typing import Tuple
from django.conf import settings
from django.db import models, transaction

from problems.models.problem import Problem
from django_enumfield import enum

from asgiref.sync import sync_to_async

class PreparationKind (enum.Enum):
    MANUAL  = 0
    POLYGON = 1

class PreparationStatus (enum.Enum):
    PENDING  = 0
    RUNNING  = 1
    SUCCESS  = 2
    FAILURE  = 3

class PreparationManager (models.Manager):
    @staticmethod
    def create_polygon_preparation (problem: Problem, polygon_pkg: str) -> "Tuple[Preparation, PolygonPreparation]":
        final_storage: str = asyncio.run( settings.STORAGE_CLIENT.reserve() )
        
        preparation = Preparation.objects.create(
            problem = problem,
            storage = final_storage,
            kind    = PreparationKind.POLYGON,
            status  = PreparationStatus.PENDING
        )
        polygon_preparation = PolygonPreparation.objects.create(
            preparation = preparation,
            pkg_storage = polygon_pkg
        )

        from problems.tasks.polygon.prepare import prepare_polygon_problem
        
        prepare_polygon_problem.delay(
            problem.pk,
            preparation.pk,
            polygon_pkg,
            final_storage
        )

        return (preparation, polygon_preparation)

    @staticmethod
    def set_preparation_status (id: int, status: PreparationStatus):
        with transaction.atomic():
            rows_updated = Preparation.objects \
                .filter(pk = id) \
                .update(status = status)
            
            if rows_updated == 0:
                raise Preparation.DoesNotExist(
                    f"Could not set preparation status for pk={id}")

        # TODO notify channel of change

    @staticmethod
    def finish_preparation (
            preparation_id:   int,
            prepared_storage: str,
            problem_id:       int
        ):
        with transaction.atomic():
            Preparation.objects.set_preparation_status(preparation_id, PreparationStatus.SUCCESS)
            Problem.objects.set_problem_location(problem_id, prepared_storage)

class Preparation (models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
    storage = models.TextField()
    kind    = enum.EnumField(PreparationKind)
    status  = enum.EnumField(PreparationStatus, default=PreparationStatus.PENDING)

    objects: "PreparationManager | models.Manager[Preparation]" = PreparationManager()

class PolygonPreparation (models.Model):
    preparation = models.ForeignKey(Preparation, on_delete=models.PROTECT)
    pkg_storage = models.TextField()
