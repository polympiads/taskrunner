
import asyncio
from datetime import timedelta

from django.core.management import call_command
from django.test import Client, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from freezegun import freeze_time

from ccs.feed.submission import SubmissionCCSJson
from ccs.models.contest import ContestProblem, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from ccs.views.submissions import REV_SUBMIT
from judge.tests.languages.test_cpp import APLUSB_PROG as CPP_APLUSB_PROG
from judge.tests.languages.test_cpp import HELLO_WORLD_PROG as CPP_HELLO_WORLD_PROG
from judge.tests.languages.test_java import APLUSB_PROG as JAVA_APLUSB_PROG
from judge.tests.languages.test_python import APLUSB_PROG as PYTHON_APLUSB_PROG
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from problems.tests.management.test_prepare_polygon_cmd import APLUSB_FILE
from storecli.inmemory import InMemoryStorageClient
from urllib.parse import urlencode
from django.core.files.uploadedfile import SimpleUploadedFile

from submit.models.submission import Submission
from submit.models.verdict import SubmissionVerdict

class TestSubmitView (TransactionTestCase):
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

    def run_request (self, username: str, contest_id: int, problem_id: int, language_id: str, content: bytes):
        if username is not None:
            session = self.login(username)
        urlparams = {}
        if problem_id is not None:  urlparams["problem_id"] = problem_id
        if language_id is not None: urlparams["language_id"] = language_id
        return Client().post(
            reverse(REV_SUBMIT, kwargs={ "pk": contest_id }) + "?" + urlencode(urlparams),
            { "file": SimpleUploadedFile("file", content) } if content is not None else {},
            headers = { "X-Session-ID": session } if username is not None else {}
        )

    def verify_valid (self, response, username: str, language_id: str, verdict: SubmissionVerdict):
        self.assertEqual(response.status_code, 201, response.content)
        json: SubmissionCCSJson = response.json()
        self.assertEqual( json["problem_id"], str(self.problem.pk) )
        self.assertEqual( json["account_id"], str(User.objects.get(username = username).pk) )
        self.assertEqual( json["language_id"], language_id)

        submission_id: int = int(json["id"])
        submission = Submission.objects.get(pk = submission_id)
        self.assertEqual( submission.verdict, verdict )
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)
    
    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk + 1, self.problem.pk, "cpp", b""),
            404, "Contest does not exist." )
        self.verify_error(
            self.run_request("user2", self.contest2.pk + 1, self.problem.pk, "cpp", b""),
            404, "Contest does not exist." )
        self.verify_error(
            self.run_request("admin", self.contest2.pk + 1, self.problem.pk, "cpp", b""),
            404, "Contest does not exist." )
    def test_contest_private (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk, self.problem.pk + 1, "cpp", b""),
            404, "Contest does not exist." )
        self.verify_error(
            self.run_request("user2", self.contest2.pk, self.problem.pk + 1, "cpp", b""),
            404, "Contest does not exist." )
        self.verify_error(
            self.run_request("admin", self.contest2.pk, self.problem.pk + 1, "cpp", b""),
            404, "Problem does not exist." )
    def test_contest_public (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk + 1, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk + 1, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk + 1, "cpp", b""),
            404, "Problem does not exist." )
    def test_contest_public_problem_not_linked (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
    def test_contest_problem_id_missing (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, None, "cpp", b""),
            400, "Missing field 'problem_id' in URL parameters." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, None, "cpp", b""),
            400, "Missing field 'problem_id' in URL parameters." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, None, "cpp", b""),
            400, "Missing field 'problem_id' in URL parameters." )
    def test_contest_problem_wrong_contest (self):
        ContestProblem.objects.create(contest = self.contest2, problem = self.problem)
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", b""),
            404, "Problem does not exist." )
    def test_contest_problem_not_prepared (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", b""),
            500, "Problem isn't prepared." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", b""),
            500, "Problem isn't prepared." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", b""),
            500, "Problem isn't prepared." )
    def test_contest_problem_prepared (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk, None, b""),
            400, "Missing field 'language_id' in URL parameters." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk, None, b""),
            400, "Missing field 'language_id' in URL parameters." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk, None, b""),
            400, "Missing field 'language_id' in URL parameters." )
    def test_contest_problem_prepared_unknown_language (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

        self.verify_error(
            self.run_request("user1", self.contest1.pk, self.problem.pk, "???", b""),
            400, "Could not recognize language id '???'." )
        self.verify_error(
            self.run_request("user2", self.contest1.pk, self.problem.pk, "???", b""),
            400, "Could not recognize language id '???'." )
        self.verify_error(
            self.run_request("admin", self.contest1.pk, self.problem.pk, "???", b""),
            400, "Could not recognize language id '???'." )
    def test_contest_problem_file_missing (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

            self.verify_error(
                self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", None),
                400, "Could not find file 'file' in POST request." )
            self.verify_error(
                self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", None),
                400, "Could not find file 'file' in POST request." )
            self.verify_error(
                self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", None),
                400, "Could not find file 'file' in POST request." )
    def test_contest_problem_prepared_not_started (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with eager_celery():
            call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

            self.verify_error(
                self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                403, "User cannot create a submission in that contest." )
            self.verify_error(
                self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                403, "Cannot create submission for contest that hasn't started." )
            self.verify_valid(
                self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                "admin", "cpp", SubmissionVerdict.ACCEPTED )
    def test_contest_problem_prepared_ended (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
        with freeze_time("2026-03-22T11:40:00.001"):
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_error(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    403, "Cannot create submission after the end of the contest." )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    "admin", "cpp", SubmissionVerdict.ACCEPTED )
    def test_contest_problem_prepared_and_started_cpp (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    "user2", "cpp", SubmissionVerdict.ACCEPTED )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_APLUSB_PROG.encode()),
                    "admin", "cpp", SubmissionVerdict.ACCEPTED )
    def test_contest_problem_prepared_and_started_cpp_limit (self):
        CPP_HELLO_WORLD_PROG_B = CPP_HELLO_WORLD_PROG.encode()
        LIMIT = 32 * 1024
        MISSING = LIMIT - len(CPP_HELLO_WORLD_PROG_B)
        CPP_HELLO_WORLD_PROG_B = CPP_HELLO_WORLD_PROG_B + b"\n" * MISSING
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    "user2", "cpp", SubmissionVerdict.WRONG_ANSWER )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    "admin", "cpp", SubmissionVerdict.WRONG_ANSWER )
    def test_contest_problem_prepared_and_started_cpp_over_the_limit (self):
        CPP_HELLO_WORLD_PROG_B = CPP_HELLO_WORLD_PROG.encode()
        LIMIT = 32 * 1024
        MISSING = LIMIT + 1 - len(CPP_HELLO_WORLD_PROG_B)
        CPP_HELLO_WORLD_PROG_B = CPP_HELLO_WORLD_PROG_B + b"\n" * MISSING
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    400, "Submitted file is too large." )
                self.verify_error(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    400, "Submitted file is too large." )
                self.verify_error(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG_B),
                    400, "Submitted file is too large." )
    def test_contest_problem_prepared_and_started_cpp_wa (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    "user2", "cpp", SubmissionVerdict.WRONG_ANSWER )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    "admin", "cpp", SubmissionVerdict.WRONG_ANSWER )
    def test_contest_problem_prepared_and_started_cpp_ce (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", (CPP_HELLO_WORLD_PROG + "\nhello\n").encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", (CPP_HELLO_WORLD_PROG + "\nhello\n").encode()),
                    "user2", "cpp", SubmissionVerdict.COMPILER_ERROR )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", (CPP_HELLO_WORLD_PROG + "\nhello\n").encode()),
                    "admin", "cpp", SubmissionVerdict.COMPILER_ERROR )
    def test_contest_problem_prepared_and_started_cpp_wa (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    "user2", "cpp", SubmissionVerdict.WRONG_ANSWER )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "cpp", CPP_HELLO_WORLD_PROG.encode()),
                    "admin", "cpp", SubmissionVerdict.WRONG_ANSWER )
    def test_contest_problem_prepared_and_started_python (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "python3", PYTHON_APLUSB_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "python3", PYTHON_APLUSB_PROG.encode()),
                    "user2", "python3", SubmissionVerdict.ACCEPTED )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "python3", PYTHON_APLUSB_PROG.encode()),
                    "admin", "python3", SubmissionVerdict.ACCEPTED )
    def test_contest_problem_prepared_and_started_java (self):
        ContestProblem.objects.create(contest = self.contest1, problem = self.problem)
        with freeze_time("2026-03-22T06:40:00"):
            ContestManager.start_contest(self.contest1.pk)
            with eager_celery():
                call_command("prepare_polygon", self.problem.pk, APLUSB_FILE)

                self.verify_error(
                    self.run_request("user1", self.contest1.pk, self.problem.pk, "java", JAVA_APLUSB_PROG.encode()),
                    403, "User cannot create a submission in that contest." )
                self.verify_valid(
                    self.run_request("user2", self.contest1.pk, self.problem.pk, "java", JAVA_APLUSB_PROG.encode()),
                    "user2", "java", SubmissionVerdict.ACCEPTED )
                self.verify_valid(
                    self.run_request("admin", self.contest1.pk, self.problem.pk, "java", JAVA_APLUSB_PROG.encode()),
                    "admin", "java", SubmissionVerdict.ACCEPTED )
