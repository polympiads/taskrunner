
import asyncio
from datetime import timedelta
from urllib.parse import urlencode

from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from ccs.models.contest import ContestProblem, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility

from django.contrib.auth.models import User
from django.core.management import call_command

from ccs.views.submissions import REV_SUBMIT, REV_VIEW_CODE
from judge.tests.languages.test_cpp import APLUSB_PROG
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from storecli.inmemory import InMemoryStorageClient
from django.core.files.uploadedfile import SimpleUploadedFile

from submit.models.submission import Submission
from django.conf import settings

class SubmissionCodeTests (TransactionTestCase):
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
        self.user3 = User.objects.create_user("user3", password = "password")
        self.admin = User.objects.create_superuser("admin", password = "password")
        self.sudo  = User.objects.create_superuser("sudo", password = "password")

        ContestManager.add_accounts(self.contest1.pk, [
            (self.user2, ContestRole.TEAM),
            (self.user3, ContestRole.TEAM),
            (self.admin, ContestRole.JUDGE),
            (self.sudo,  ContestRole.JUDGE)
        ])
        ContestManager.add_accounts(self.contest2.pk, [
            (self.user2, ContestRole.TEAM),
            (self.user3, ContestRole.TEAM),
            (self.admin, ContestRole.JUDGE),
            (self.sudo,  ContestRole.JUDGE)
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
            STORAGE_CLIENT = InMemoryStorageClient(settings.STORAGE_CLIENT_LOCATION)
        )
        self.new_settings.__enter__()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)
    def login (self, username: str):
        return Client().get("/login/", { "username": username, "password": "password" }).json()['session_id']
    
    def run_submit (self, username: str, contest_id: int, problem_id: int, language_id: str, content: bytes):
        with eager_celery():
            if username is not None:
                session = self.login(username)
            urlparams = {}
            if problem_id is not None:  urlparams["problem_id"] = problem_id
            if language_id is not None: urlparams["language_id"] = language_id
            response = Client().post(
                reverse(REV_SUBMIT, kwargs={ "pk": contest_id }) + "?" + urlencode(urlparams),
                { "file": SimpleUploadedFile("file", content) } if content is not None else {},
                headers = { "X-Session-ID": session } if username is not None else {}
            )

            self.assertEqual(response.status_code, 201, response.content)
    def run_view_code (self, username: str, contest_id: int, submission_id: int):
        if username is not None:
            session = self.login(username)
        
        return Client().get(
            reverse(REV_VIEW_CODE, kwargs = { "pk": contest_id, "subpk": submission_id }),
            headers = { "X-Session-ID": session } if username is not None else {}
        )

    def prepare_problem (self, contest):
        ContestProblem.objects.create(contest = contest, problem = self.problem)
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)
        ContestManager.start_contest(contest.pk)

    def verify_valid (self, response, content):
        if response.status_code != 200:
            self.assertEqual(response.status_code, 200, response.content)
        response_content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(response_content, content)
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)

    def test_contest_does_not_exist (self):
        for user in [ "user1", "user2", "user3", "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk + 1, 1),
                404, "Contest does not exist." )
    def test_contest_private (self):
        for user in [ "user1", "user2", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, 1),
                404, "Contest does not exist." )
        for user in [ "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, 1),
                404, "Submission does not exist." )
    def test_contest_public (self):
        for user in [ "user1", "user2", "user3", "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest1.pk, 1),
                404, "Submission does not exist." )

    def test_simple_user_submitted (self):
        self.prepare_problem(self.contest1)
        self.run_submit("user2", self.contest1.pk, self.problem.pk, "cpp", APLUSB_PROG.encode())

        for user in [ "user1", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest1.pk, Submission.objects.last().pk),
                404, "Submission does not exist." )
        for user in [ "user2", "admin", "sudo" ]:
            self.verify_valid(
                self.run_view_code(user, self.contest1.pk, Submission.objects.last().pk),
                APLUSB_PROG.encode() )
        for user in [ "user1", "user2", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                404, "Contest does not exist." )
        for user in [ "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                404, "Submission does not exist." )
    def test_judge_submitted (self):
        self.prepare_problem(self.contest1)
        self.run_submit("admin", self.contest1.pk, self.problem.pk, "cpp", APLUSB_PROG.encode())
        
        for user in [ "user1", "user2", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest1.pk, Submission.objects.last().pk),
                404, "Submission does not exist." )
        for user in [ "admin", "sudo" ]:
            self.verify_valid(
                self.run_view_code(user, self.contest1.pk, Submission.objects.last().pk),
                APLUSB_PROG.encode() )
        for user in [ "user1", "user2", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                404, "Contest does not exist." )
        for user in [ "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                404, "Submission does not exist." )
    def test_judge_submitted_private (self):
        self.prepare_problem(self.contest2)
        self.run_submit("admin", self.contest2.pk, self.problem.pk, "cpp", APLUSB_PROG.encode())
        
        for user in [ "user1", "user2", "user3" ]:
            self.verify_error(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                404, "Contest does not exist." )
        for user in [ "admin", "sudo" ]:
            self.verify_valid(
                self.run_view_code(user, self.contest2.pk, Submission.objects.last().pk),
                APLUSB_PROG.encode() )
        for user in [ "user1", "user2", "user3", "admin", "sudo" ]:
            self.verify_error(
                self.run_view_code(user, self.contest1.pk, Submission.objects.last().pk),
                404, "Submission does not exist." )
