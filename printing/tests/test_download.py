
import asyncio
from datetime import timedelta
import hashlib
import json

from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ccs.models.contest import ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from judge.tests.languages.test_cpp import APLUSB_PROG, HELLO_WORLD_PROG
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from printing.ccs import ccs_json_from_print
from printing.models import ContestPrint, PrintStatus
from printing.views.admin import REV_PRINT_DONE
from printing.views.download import REV_PRINT_DOWNLOAD
from printing.views.print import REV_PRINT_CREATE
from storecli.inmemory import InMemoryStorageClient

from django.contrib.auth.models import User

class TestCreateView (TransactionTestCase):
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

        ContestManager.add_accounts(self.contest1.pk, [ (self.user2, ContestRole.TEAM), (self.admin, ContestRole.JUDGE) ])
        ContestManager.add_accounts(self.contest2.pk, [ (self.user2, ContestRole.TEAM), (self.admin, ContestRole.JUDGE) ])

        self.storage_client = InMemoryStorageClient("/tmp")
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
            STORAGE_CLIENT = self.storage_client
        )
        self.new_settings.__enter__()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)

    def login (self, username: str):
        return Client().get("/login/", { "username": username, "password": "password" }).json()['session_id']

    def verify_valid (self, response, content: bytes):
        if response.status_code != 200:
            self.assertEqual(response.status_code, 200, response.content)
        response_content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(response_content, content)
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)
    
    def run_print (self, username: str, contest_id: int, content: bytes):
        with eager_celery():
            if username is not None:
                session = self.login(username)
            return int(Client().post(
                reverse(REV_PRINT_CREATE, kwargs={ "pk": contest_id }),
                { "file": SimpleUploadedFile("file", content) } if content is not None else {},
                headers = { "X-Session-ID": session } if username is not None else {}
            ).json()["id"])
    def run_download (self, username: str, contest_id: int, print_id: int, kind: str):
        with eager_celery():
            if username is not None:
                session = self.login(username)
            return Client().get(
                reverse(REV_PRINT_DOWNLOAD, kwargs={ "pk": contest_id, "prpk": print_id, "kind": kind }),
                headers = { "X-Session-ID": session } if username is not None else {}
            )

    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_download("user1", self.contest2.pk + 1, 1, "yes"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_download("user2", self.contest2.pk + 1, 1, "yes"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_download("admin", self.contest2.pk + 1, 1, "yes"),
            404, "Contest does not exist.")
    def test_private_contest (self):
        self.verify_error(
            self.run_download("user1", self.contest2.pk, 1, "yes"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_download("user2", self.contest2.pk, 1, "yes"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_download("admin", self.contest2.pk, 1, "yes"),
            404, "Print Object does not exist.")
    def test_public_contest (self):
        self.verify_error(
            self.run_download("user1", self.contest1.pk, 1, "yes"),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_download("user2", self.contest1.pk, 1, "yes"),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_download("admin", self.contest1.pk, 1, "yes"),
            404, "Print Object does not exist.")
    def test_invalid_kind (self):
        print_id = self.run_print("user2", self.contest1.pk, HELLO_WORLD_PROG.encode())
        self.verify_error(
            self.run_download("user1", self.contest1.pk, print_id, "yes"),
            401, "Invalid Print Kind.")
        self.verify_error(
            self.run_download("user2", self.contest1.pk, print_id, "yes"),
            401, "Invalid Print Kind.")
        self.verify_error(
            self.run_download("admin", self.contest1.pk, print_id, "yes"),
            401, "Invalid Print Kind.")
    def test_download_code (self):
        print_id = self.run_print("user2", self.contest1.pk, HELLO_WORLD_PROG.encode())
        self.verify_error(
            self.run_download("user1", self.contest1.pk, print_id, "code"),
            404, "Print Object does not exist.")
        self.verify_valid(
            self.run_download("user2", self.contest1.pk, print_id, "code"),
            HELLO_WORLD_PROG.encode())
        self.verify_valid(
            self.run_download("admin", self.contest1.pk, print_id, "code"),
            HELLO_WORLD_PROG.encode())
    
    def test_different_kind (self):
        print_id = ContestPrint.objects.create(
            contest = self.contest1,
            owner = self.user2,
            status = PrintStatus.PENDING,

            code_location = "code",
            pdf_location = "pdf",
            err_location = "err",
            simple_error = None
        ).pk

        self.storage_client.put("code", b"code/content", ".txt")
        self.storage_client.put("pdf",  b"pdf/content",  ".txt")
        self.storage_client.put("err",  b"err/content",  ".txt")

        self.verify_error(
            self.run_download("user1", self.contest1.pk, print_id, "code"),
            404, "Print Object does not exist.")
        self.verify_valid(
            self.run_download("user2", self.contest1.pk, print_id, "code"),
            b"code/content")
        self.verify_valid(
            self.run_download("admin", self.contest1.pk, print_id, "code"),
            b"code/content")
        
        self.verify_error(
            self.run_download("user1", self.contest1.pk, print_id, "pdf"),
            404, "Print Object does not exist.")
        self.verify_valid(
            self.run_download("user2", self.contest1.pk, print_id, "pdf"),
            b"pdf/content")
        self.verify_valid(
            self.run_download("admin", self.contest1.pk, print_id, "pdf"),
            b"pdf/content")
        
        self.verify_error(
            self.run_download("user1", self.contest1.pk, print_id, "err"),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_download("user2", self.contest1.pk, print_id, "err"),
            404, "Print Object does not exist.")
        self.verify_valid(
            self.run_download("admin", self.contest1.pk, print_id, "err"),
            b"err/content")
