
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
from judge.tests.languages.test_cpp import APLUSB_PROG
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from printing.ccs import ccs_json_from_print
from printing.models import ContestPrint, PrintStatus
from printing.views.admin import REV_PRINT_DONE
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

    def verify_valid (self, response, file: str, hash: bytes):
        self.assertEqual(response.status_code, 201, response.content)

        print = ContestPrint.objects.last()
        if print.status == PrintStatus.FAILURE:
            content = self.storage_client.in_memory[print.err_location][0]
            assert False, "Invalid status: " + str(content)
        if print.status == PrintStatus.ERROR:
            assert False, "Invalid status: " + print.simple_error
        
        self.assertEqual(print.status, PrintStatus.READY)
        content = self.storage_client.in_memory[print.pdf_location][0]

        print.status = PrintStatus.PENDING
        print.pdf_location = None
        print.err_location = None
        print.simple_error = None

        self.assertEqual(response.json(), ccs_json_from_print(print))
        with open(file, "wb") as _file: _file.write(content)
        self.assertEqual(hashlib.sha256(content).hexdigest(), hash)
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)
    
    def run_request (self, username: str, contest_id: int, content: bytes):
        with eager_celery():
            if username is not None:
                session = self.login(username)
            return Client().post(
                reverse(REV_PRINT_CREATE, kwargs={ "pk": contest_id }),
                { "file": SimpleUploadedFile("file", content) } if content is not None else {},
                headers = { "X-Session-ID": session } if username is not None else {}
            )

    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk + 1, None),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk + 1, None),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk + 1, None),
            404, "Contest does not exist.")
    def test_private_contest (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk, None),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, None),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk, None),
            400, "Could not find file 'file' in POST request.")
    def test_public_contest (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, None),
            403, "Cannot print for that contest.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, None),
            400, "Could not find file 'file' in POST request.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, None),
            400, "Could not find file 'file' in POST request.")
    def test_public_contest_hello_world (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, APLUSB_PROG.encode()),
            403, "Cannot print for that contest.")
        self.verify_valid(
            self.run_request("user2", self.contest1.pk, APLUSB_PROG.encode()),
            "pdfs_user2_helloworld.pdf", "cbbcab277ab3a744255949e7ba4c7e9c4f9874a6eb12c0be84e1e71704799a49")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, APLUSB_PROG.encode()),
            "pdfs_admin_helloworld.pdf", "45c26740178abadfe9ec6b56c1b793ea7f6335757fae9d641740f0604fb460c5")
    def test_public_contest_close_to_limit (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_valid(
            self.run_request("user2", self.contest1.pk, ((b"a a " + b"a" * 80 + b" a a\n") * 128)[:32768]),
            "pdfs_user2_close_limit.pdf", "4926a7d2751fcb0788359b512ec7fb2c7bd41215775bd27b1792644907b33161")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, ((b"a a " + b"a" * 80 + b" a a\n") * 128)[:32768]),
            "pdfs_admin_close_limit.pdf", "1f393a052cec890e9303c576b775da7983d283e02f278775512f9abe4e8fb053")
    def test_public_contest_above_word_limit (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, ((b"a a " + b"a" * 81 + b" a a\n") * 128)[:32768]),
            400, "Submitted file has a word too long.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, ((b"a a " + b"a" * 81 + b" a a\n") * 128)[:32768]),
            400, "Submitted file has a word too long.")
    def test_public_contest_close_to_limit_with_words (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_valid(
            self.run_request("user2", self.contest1.pk, ((b"a " * 127 + b"a\n") * 128)[:32768]),
            "pdfs_user2_close_limit_ww.pdf", "826e665f78f47a6245bff9f9bb519451a007b94a07f9d8c856af9d17bad66e8e")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, ((b"a " * 127 + b"a\n") * 128)[:32768]),
            "pdfs_admin_close_limit_ww.pdf", "3c01276ab1d5b9c94b0ac4048e5dde197a63c020dae420afa45595a7d0b676a8")
    def test_public_contest_over_the_limit (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, ((b"a" * 256 + b"\n") * 128)[:32769]),
            400, "Submitted file is too large.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, ((b"a" * 256 + b"\n") * 128)[:32769]),
            400, "Submitted file is too large.")
    def test_public_contest_lc_close_to_limit (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_valid(
            self.run_request("user2", self.contest1.pk, b"a\n" * (512)),
            "pdfs_user2_lc_close_limit.pdf", "eb7e759458a2fff47a10b57e80a9eecd9d7c1e1427d2687a85dd4538c3ff9f77")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, b"a\n" * (512)),
            "pdfs_admin_lc_close_limit.pdf", "c4cd5b7f1690e462dba20fb507f748ccfb4bbada52dbaebdf80afd8d51b3ae56")
    def test_public_contest_lc_over_the_limit (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, b""),
            403, "Cannot print for that contest.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, b"a\n" * (512 + 1)),
            400, "Submitted file has too many lines.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, b"a\n" * (512 + 1)),
            400, "Submitted file has too many lines.")
