
import asyncio
import os
from django.conf import settings
from django.core.management import BaseCommand

from problems.models.preparation import Preparation
from problems.models.problem import Problem
from problems.telemetry import start_as_current_span

from asgiref.sync import async_to_sync

class Command (BaseCommand):
    help = "Upload a polygon package for a given problem"

    def add_arguments(self, parser):
        parser.add_argument("problem_id", type=int, help="The ID of the problems package")
        parser.add_argument("package", type=str, help="path of the zip file")

    def handle(self, *args, **options):
        problem_id = options['problem_id']
        package    = options['package']

        problem = Problem.objects.get(pk = problem_id)
        if not os.path.exists(package):
            raise FileNotFoundError(f"Could not find polygon package: {package}")

        async def run_upload ():
            location = settings.STORAGE_CLIENT.reserve()

            await settings.STORAGE_CLIENT.upload(package, location)

            return location

        with start_as_current_span("Prepare.polygon"):
            pkg_location = async_to_sync(run_upload)()

            Preparation.objects.create_polygon_preparation(
                problem,
                pkg_location
            )
