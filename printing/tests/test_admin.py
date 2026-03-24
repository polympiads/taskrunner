
import asyncio
from datetime import timedelta
import json

from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from ccs.models.contest import ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from printing.models import ContestPrint, PrintStatus
from printing.views.admin import REV_PRINT_DONE
from storecli.inmemory import InMemoryStorageClient

from django.contrib.auth.models import User
from django.conf import settings

class TestDoneView (TransactionTestCase):
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

        self.storage_client = InMemoryStorageClient(settings.STORAGE_CLIENT_LOCATION)
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

    def run_request (self, username: str, contest_id: int, print_id: int):
        if username is not None:
            session = self.login(username)
        return Client().post(
            reverse(REV_PRINT_DONE, kwargs={ "pk": contest_id, "prpk": print_id }),
            headers = { "X-Session-ID": session } if username is not None else {}
        )

    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)

    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk + 1, 1),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk + 1, 1),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk + 1, 1),
            404, "Contest does not exist.")
    def test_contest_private (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk, 1),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, 1),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk, 1),
            404, "Print Object does not exist.")
    def test_contest_public (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, 1),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, 1),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, 1),
            404, "Print Object does not exist.")
    def test_contest_print_exists_wrong_contest (self):
        print = ContestPrint.objects.create(
            contest = self.contest2,
            owner = self.user1,
            code_location = ""
        )

        self.verify_error(
            self.run_request("user1", self.contest1.pk, print.pk),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, print.pk),
            404, "Print Object does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, print.pk),
            404, "Print Object does not exist.")
    def test_contest_print_exists (self):
        print = ContestPrint.objects.create(
            contest = self.contest1,
            owner = self.user1,
            code_location = "",
            status = PrintStatus.READY
        )

        self.verify_error(
            self.run_request("user1", self.contest1.pk, print.pk),
            403, "Cannot modify Print Object.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, print.pk),
            403, "Cannot modify Print Object.")
        
        response = self.run_request("admin", self.contest1.pk, print.pk)
        resp_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resp_json,
            { "id": str(print.pk), "owner_id": str(self.user1.pk), "status": "done",
             "code_href": f"/contests/{print.contest.pk}/prints/{print.pk}/download/code/" })

        feed = list( EventFeed.objects.all() )
        self.assertEqual(len(feed), 1)
        feed = feed[0]
        self.assertEqual(feed.visibility, Visibility.PRIVATE)
        self.assertEqual(feed.owner.pk, self.user1.pk)
        self.assertEqual(
            json.loads(feed.full_payload),
            { "type": "prints", "token": str(feed.pk), "id": str(print.pk), "data": resp_json })
        print.refresh_from_db()
        self.assertEqual(print.contest.pk, self.contest1.pk)
        self.assertEqual(print.owner.pk, self.user1.pk)
        self.assertEqual(print.status, PrintStatus.DONE)
        self.assertEqual(print.code_location, "")
        self.assertEqual(print.err_location, None)
        self.assertEqual(print.pdf_location, None)
        self.assertEqual(print.simple_error, None)

    def test_contest_print_exists_wrong_state (self):
        for status in [ PrintStatus.COMPILING, PrintStatus.ERROR, PrintStatus.FAILURE, PrintStatus.PENDING, PrintStatus.FAILURE ]:
            print = ContestPrint.objects.create(
                contest = self.contest1,
                owner = self.user1,
                code_location = "",
                status = status
            )
            self.verify_error(
                self.run_request("user1", self.contest1.pk, print.pk),
                403, "Cannot modify Print Object.")
            self.verify_error(
                self.run_request("user2", self.contest1.pk, print.pk),
                403, "Cannot modify Print Object.")
            self.verify_error(
                self.run_request("admin", self.contest1.pk, print.pk),
                401, "Cannot make print DONE if it isn't READY.")
