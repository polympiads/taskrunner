
import asyncio
from datetime import timedelta
import json

from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.views import View

from balloons.ccs import ccs_json_from_ballon
from balloons.models import Balloon, BalloonStatus
from balloons.views import REV_BALLOON_SET_STATUS
from ccs.models.contest import ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from judge.tests.tasks.icpc.test_scheduler import eager_celery
from problems.models.problem import Problem
from storecli.inmemory import InMemoryStorageClient

from django.contrib.auth.models import User

class TestSetBalloonStatusView (TransactionTestCase):
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

        self.problem = Problem.objects.create()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)

    def login (self, username: str):
        return Client().get("/login/", { "username": username, "password": "password" }).json()['session_id']
    
    def verify_valid (self, response):
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {})
    def verify_error (self, response, code: int, message: str):
        self.assertEqual(response.status_code, code, response.content)
        self.assertEqual(response.json(), { "code": code, "message": message }, response.content)
    
    def run_request (self, username: str, contest_id: int, balloon_id: int, status: str):
        with eager_celery():
            if username is not None:
                session = self.login(username)
            return Client().post(
                reverse(REV_BALLOON_SET_STATUS, kwargs={ "pk": contest_id, "blpk": balloon_id }) + (f"?status={status}" if status is not None else ""),
                headers = { "X-Session-ID": session } if username is not None else {}
            )

    def test_contest_does_not_exist (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk + 1, 1, "pending"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk + 1, 1, "pending"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk + 1, 1, "pending"),
            404, "Contest does not exist.")
    def test_contest_private (self):
        self.verify_error(
            self.run_request("user1", self.contest2.pk, 1, "pending"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("user2", self.contest2.pk, 1, "pending"),
            404, "Contest does not exist.")
        self.verify_error(
            self.run_request("admin", self.contest2.pk, 1, "pending"),
            404, "Balloon does not exist.")
    def test_contest_public (self):
        self.verify_error(
            self.run_request("user1", self.contest1.pk, 1, "pending"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, 1, "pending"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, 1, "pending"),
            404, "Balloon does not exist.")
    def test_contest_balloon_exists_status_none (self):
        balloon = Balloon.create_balloon( self.contest1, self.user2, self.problem )
        self.verify_error(
            self.run_request("user1", self.contest1.pk, balloon.pk, None),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, balloon.pk, None),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, balloon.pk, None),
            400, "Field 'status' missing in url parameters.")
    def test_contest_balloon_exists_status_invalid (self):
        balloon = Balloon.create_balloon( self.contest1, self.user2, self.problem )
        self.verify_error(
            self.run_request("user1", self.contest1.pk, balloon.pk, "yes"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, balloon.pk, "yes"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("admin", self.contest1.pk, balloon.pk, "yes"),
            400, "Could not recognize status string 'yes'.")

    def test_contest_balloon_exists_set_status (self):
        balloon = Balloon.create_balloon( self.contest1, self.user2, self.problem )

        self.assertEqual(balloon.status, BalloonStatus.PENDING)
        self.verify_error(
            self.run_request("user1", self.contest1.pk, balloon.pk, "taken"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, balloon.pk, "taken"),
            403, "Cannot modify balloon state.")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "taken"))
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "taken"))
        
        balloon.refresh_from_db()
        self.assertEqual(balloon.status, BalloonStatus.TAKEN)
        
        self.verify_error(
            self.run_request("user1", self.contest1.pk, balloon.pk, "dropped"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, balloon.pk, "dropped"),
            403, "Cannot modify balloon state.")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "dropped"))
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "dropped"))

        balloon.refresh_from_db()
        self.assertEqual(balloon.status, BalloonStatus.DROPPED)
        
        self.verify_error(
            self.run_request("user1", self.contest1.pk, balloon.pk, "pending"),
            403, "Cannot modify balloon state.")
        self.verify_error(
            self.run_request("user2", self.contest1.pk, balloon.pk, "pending"),
            403, "Cannot modify balloon state.")
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "pending"))
        self.verify_valid(
            self.run_request("admin", self.contest1.pk, balloon.pk, "pending"))
        
        balloon.refresh_from_db()
        self.assertEqual(balloon.status, BalloonStatus.PENDING)

        feed =list(reversed( list( EventFeed.objects.all() ) ))
        for kind in [ BalloonStatus.PENDING, BalloonStatus.TAKEN, BalloonStatus.DROPPED, BalloonStatus.PENDING ]:
            x_feed = feed.pop()
            balloon.status = kind
            self.assertEqual(json.loads(x_feed.full_payload), {
                "data": ccs_json_from_ballon(balloon),
                "token": str(x_feed.pk),
                "type": "balloons",
                "id": str(balloon.pk)
            })
