
import asyncio
from datetime import timedelta

from django.core.management import call_command
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from ccs.models.contest import ContestProblem, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility

from django.contrib.auth.models import User

from ccs.views.problem import REV_STATEMENT
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from storecli.inmemory import InMemoryStorageClient
from storecli.problems.storage import ProblemStorage

class TestProblemStatement (TransactionTestCase):
    def setUp(self):
        self.contest1 = asyncio.run( ContestManager.acreate_contest(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
        self.contest2 = asyncio.run( ContestManager.acreate_contest(
            name         = "prvct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PRIVATE
        ) )

        self.user1 = User.objects.create_user("user1", password = "password")
        self.user2 = User.objects.create_user("user2", password = "password")
        self.admin = User.objects.create_superuser("admin", password = "password")

        ContestManager.add_accounts(self.contest1.pk, [
            (self.user2, ContestRole.TEAM),
            (self.admin, ContestRole.JUDGE)
        ])
        ContestManager.add_accounts(self.contest2.pk, [
            (self.user2, ContestRole.TEAM),
            (self.admin, ContestRole.JUDGE)
        ])

        self.problem = Problem.objects.create()
        self.new_settings = override_settings(
            ROOT_URLCONF="ccs.urls",            
            MIDDLEWARE = [
                'django.middleware.security.SecurityMiddleware',
                'ccs.auth.middleware.HeaderSessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],
            STORAGE_CLIENT = InMemoryStorageClient("/tmp")
        )
        self.new_settings.__enter__()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)
    def login (self, username: str):
        return Client().get("/login/", { "username": username, "password": "password" }).json()['session_id']

    def run_request (self, username: str, contest_id: int, problem_id: int):
        session = self.login(username)
        return Client().get(
            reverse(REV_STATEMENT, kwargs={ "pk": contest_id, "pbpk": problem_id }),
            headers = { "X-Session-ID": session }
        )
    def verify_valid (self, response, content: bytes):
        response_content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response_content, content)
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)
    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk + 1, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk + 1, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk + 1, self.problem.pk),
            404, "Contest does not exist.")
    def test_contest_private (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk, self.problem.pk),
            404, "Problem does not exist.")
    def test_contest_public (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk),
            403, "Contest hasn't started yet.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk),
            403, "Contest hasn't started yet.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
    def test_contest_public_started (self):
        ContestManager.start_contest(self.contest1.pk)
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk + 1),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk + 1),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk + 1),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        ContestProblem.objects.create(contest = self.contest2, problem = self.problem, label = "A")
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk),
            404, "Problem does not exist.")
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem, label = "A")
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk),
            500, "Problem isn't prepared.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk),
            500, "Problem isn't prepared.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk),
            500, "Problem isn't prepared.")
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)
        self.problem = Problem.objects.get(pk = self.problem.pk)

        storage = asyncio.run(ProblemStorage.download(self.problem.problem_location))
        with open(storage.get_statement(), "rb") as file:
            content = file.read()
        self.verify_valid(
            self.run_request("user1", self.contest1.pk, self.problem.pk),
            content)
        self.verify_valid(
            self.run_request("user2", self.contest1.pk, self.problem.pk),
            content)
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, self.problem.pk),
            content)
    def test_contest_private_started (self):
        ContestManager.start_contest(self.contest2.pk)
        self.verify_error(
            self.run_request("user1", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk, self.problem.pk),
            404, "Problem does not exist.")
        ContestProblem.objects.create(contest = self.contest2, problem = self.problem, label = "A")
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)
        self.problem = Problem.objects.get(pk = self.problem.pk)

        storage = asyncio.run(ProblemStorage.download(self.problem.problem_location))
        with open(storage.get_statement(), "rb") as file:
            content = file.read()
        self.verify_error(
            self.run_request("user1", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, self.problem.pk),
            404, "Contest does not exist.")
        self.verify_valid(
            self.run_request("admin", self.contest2.pk, self.problem.pk),
            content)
