
import asyncio
import json

from django.test import Client, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from freezegun import freeze_time

from ccs.models.clarification import Clarification
from ccs.models.contest import Contest, ContestProblem, ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager

from datetime import timedelta

from ccs.models.visible import Visibility
from problems.models.problem import Problem

class TestClarificationViews (TransactionTestCase):
    def setUp(self):
        self.contest1 = asyncio.run( ContestManager.acreate_contest(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
        self.contest4 = asyncio.run( ContestManager.acreate_contest(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
        ContestManager.start_contest(self.contest1.pk)
        self.contest2 = asyncio.run( ContestManager.acreate_contest(
            name         = "pubct-started",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        ) )
        with freeze_time("2026-03-19T21:00:00"):
            ContestManager.start_contest(self.contest2.pk)
        self.contest3 = asyncio.run( ContestManager.acreate_contest(
            name         = "prvct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PRIVATE
        ) )
        ContestManager.start_contest(self.contest3.pk)

        self.user1 = User.objects.create_user("user1", password = "password")
        self.user2 = User.objects.create_user("user2", password = "password")
        self.user3 = User.objects.create_user("user3", password = "password")
        self.admin = User.objects.create_superuser("admin", password = "password")

        ContestManager.add_accounts(self.contest2.pk, [ (self.user2, ContestRole.TEAM), (self.user3, ContestRole.TEAM), (self.admin, ContestRole.JUDGE) ])
        ContestManager.add_accounts(self.contest4.pk, [ (self.user2, ContestRole.TEAM), (self.admin, ContestRole.JUDGE) ])

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
            ]
        )
        self.new_settings.__enter__()

        EventFeed.objects.all().delete()
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)
    
    def login (self, username: str, password: str):
        return Client().get("/login/", { "username": username, "password": "password" }).json()['session_id']
    def run_request (self, username: str, contest_pk: int, data, content_type = "application/json"):
        session = self.login(username, "password")

        return Client().post(
            f"/contests/{contest_pk}/clarifications/",
            data = json.dumps( data ) if content_type == "application/json" else data,
            content_type = content_type,
            headers = { "X-Session-ID": session }
        )

    def test_run_request_not_json (self):
        response = self.run_request("user1", 0, "not-json", content_type="text/plain")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), { "code": 400, "message": "Invalid JSON body." })
    def test_run_request_no_text (self):
        response = self.run_request("user1", 0, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), { "code": 400, "message": "Field 'text' is required and must be a non-empty string." })
        response = self.run_request("user1", 0, { "text": " \n \t" })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), { "code": 400, "message": "Field 'text' is required and must be a non-empty string." })
    def test_run_request_bad_contest (self):
        response = self.run_request("user1", 0, { "text": "some text." })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), { "code": 404, "message": "Contest does not exist." })
    def test_run_request_not_private (self):
        response = self.run_request("user1", self.contest3.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 404, "message": "Contest does not exist." })
        self.assertEqual(response.status_code, 404)
        response = self.run_request("admin", self.contest3.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "User is not registered in contest." })
        self.assertEqual(response.status_code, 403)
    def test_run_request_public_started_not_registered (self):
        response = self.run_request("user1", self.contest1.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "User is not registered in contest." })
        self.assertEqual(response.status_code, 403)
        response = self.run_request("user2", self.contest1.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "User is not registered in contest." })
        self.assertEqual(response.status_code, 403)
        response = self.run_request("admin", self.contest1.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "User is not registered in contest." })
        self.assertEqual(response.status_code, 403)
    def test_run_request_public_not_started (self):
        response = self.run_request("user1", self.contest4.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "Can't send clarification before contest start." })
        self.assertEqual(response.status_code, 403)
        response = self.run_request("admin", self.contest4.pk, { "text": "some text." })
        self.assertEqual(response.json(), { "code": 403, "message": "Can't send clarification before contest start." })
        self.assertEqual(response.status_code, 403)

    def test_run_request_public_started (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("user1", self.contest2.pk, { "text": "some text." })
            self.assertEqual(response.json(), { "code": 403, "message": "User is not registered in contest." })
            self.assertEqual(response.status_code, 403)
            response = self.run_request("user2", self.contest2.pk, { "text": "some text." })
            json1 = response.json()
            uuid1 = json1["id"]
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": str(self.user2.pk),
                "problem_id": None,
                "reply_to_id": None,
                "broadcast": False,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)
            response = self.run_request("admin", self.contest2.pk, { "text": "some text." })
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": None,
                "problem_id": None,
                "reply_to_id": None,
                "broadcast": False,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)
            json2 = response.json()
            uuid2 = json2["id"]

            evt = EventFeed.objects.all()[0].pk
            self.assertEqual(EventFeed.objects.all()[0].visibility, Visibility.PRIVATE)
            self.assertEqual(EventFeed.objects.all()[1].visibility, Visibility.PRIVATE)
            self.assertEqual(EventFeed.objects.all()[0].owner, self.user2)
            self.assertEqual(EventFeed.objects.all()[1].owner, self.admin)
            self.assertEqual(json.loads(EventFeed.objects.all()[0].full_payload),
                { "type": "clarifications", "token": str(evt), "id": uuid1, "data": json1 })
            self.assertEqual(json.loads(EventFeed.objects.all()[1].full_payload),
                { "type": "clarifications", "token": str(evt + 1), "id": uuid2, "data": json2 })
    def test_run_request_on_problem (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "problem_id": "hi" })
            self.assertEqual(response.json(), { "code": 400, "message": "Field 'problem_id' must be an integer." })
            self.assertEqual(response.status_code, 400)

            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "problem_id": 1 })
            self.assertEqual(response.json(), { "code": 404, "message": "Problem does not exist." })
            self.assertEqual(response.status_code, 404)

            pb = Problem.objects.create()
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "problem_id": pb.pk })
            self.assertEqual(response.json(), { "code": 404, "message": "Problem does not exist on that contest." })
            self.assertEqual(response.status_code, 404)

            ContestProblem.objects.create(problem = pb, contest = self.contest2, label = "A")
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "problem_id": pb.pk })
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": str(self.user2.pk),
                "problem_id": str(pb.pk),
                "reply_to_id": None,
                "broadcast": False,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)

    def test_run_broadcast_false_request (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "broadcast": False })
            json1 = response.json()
            uuid1 = json1["id"]
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": str(self.user2.pk),
                "problem_id": None,
                "reply_to_id": None,
                "broadcast": False,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": False })
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": None,
                "problem_id": None,
                "reply_to_id": None,
                "broadcast": False,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)
            json2 = response.json()
            uuid2 = json2["id"]

            evt = EventFeed.objects.all()[0].pk
            self.assertEqual(EventFeed.objects.all()[0].visibility, Visibility.PRIVATE)
            self.assertEqual(EventFeed.objects.all()[1].visibility, Visibility.PRIVATE)
            self.assertEqual(EventFeed.objects.all()[0].owner, self.user2)
            self.assertEqual(EventFeed.objects.all()[1].owner, self.admin)
            self.assertEqual(json.loads(EventFeed.objects.all()[0].full_payload),
                { "type": "clarifications", "token": str(evt), "id": uuid1, "data": json1 })
            self.assertEqual(json.loads(EventFeed.objects.all()[1].full_payload),
                { "type": "clarifications", "token": str(evt + 1), "id": uuid2, "data": json2 })

    def test_run_broadcast_true_request (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "broadcast": "true" })
            self.assertEqual(response.json(), { "code": 400, "message": "Field 'broadcast' must be a boolean." })
            self.assertEqual(response.status_code, 400)
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "broadcast": True })
            self.assertEqual(response.json(), { "code": 403, "message": "Only judges can broadcast a clarification." })
            self.assertEqual(response.status_code, 403)
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": True })
            self.assertEqual(response.json(), {
                "contest_time": "0:10:23.000",
                "time": "2026-03-19T21:10:23.000Z",
                "from_team_id": None,
                "problem_id": None,
                "reply_to_id": None,
                "broadcast": True,
                "text": "some text.",
                "id": str(Clarification.objects.last().pk) })
            self.assertEqual(response.status_code, 201)
            json2 = response.json()
            uuid2 = json2["id"]

            evt = EventFeed.objects.all()[0].pk
            self.assertEqual(EventFeed.objects.all()[0].visibility, Visibility.PUBLIC)
            self.assertEqual(EventFeed.objects.all()[0].owner, self.admin)
            self.assertEqual(json.loads(EventFeed.objects.all()[0].full_payload),
                { "type": "clarifications", "token": str(evt), "id": uuid2, "data": json2 })

    def test_reply_to (self):
        with freeze_time("2026-03-19T21:10:23"):
            feed = []
            ownership = [(Visibility.PRIVATE, self.user2), (Visibility.PRIVATE, self.user2),
                (Visibility.PRIVATE, self.user2), (Visibility.PRIVATE, self.user2),
                (Visibility.PRIVATE, self.user2), (Visibility.PUBLIC, self.user2)]

            response = self.run_request("user2", self.contest2.pk, { "text": "some text." })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())
            response = self.run_request("admin", self.contest2.pk, { "text": "reply 1", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())
            response = self.run_request("admin", self.contest2.pk, { "text": "additional", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())
            response = self.run_request("user2", self.contest2.pk, { "text": "unsure", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())
            response = self.run_request("user2", self.contest2.pk, { "text": "really unsure", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())
            response = self.run_request("admin", self.contest2.pk, { "text": "right", "reply_to": int(response.json()["id"]), "broadcast": True })
            self.assertEqual(response.status_code, 201)
            feed.append(response.json())

            self.assertEqual(len(EventFeed.objects.all()), len(feed))

            for u, v in zip(feed, feed[1:]):
                self.assertEqual(u["id"], v["reply_to_id"])

            for u, v, (z, w) in zip(EventFeed.objects.all(), feed, ownership):
                self.assertEqual(u.owner, w)
                self.assertEqual(u.visibility, z)
                self.assertEqual(
                    json.loads(u.full_payload),
                    { "type": "clarifications", "token": str(u.pk), "id": v["id"], "data": v }
                )

    def test_reply_to_does_not_exist (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("user2", self.contest2.pk, { "text": "some text." })
            self.assertEqual(response.status_code, 201)
            old_resp = response
            response = self.run_request("user3", self.contest2.pk, { "text": "reply 1", "reply_to": int(response.json()["id"]) - 1 })
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), { "code": 404, "message": "Cannot reply to clarification that doesn't exist." })
            response = old_resp
            response = self.run_request("user3", self.contest2.pk, { "text": "reply 1", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), { "code": 404, "message": "Cannot reply to clarification that doesn't exist." })
            response = old_resp
            response = self.run_request("user2", self.contest2.pk, { "text": "reply 1", "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)
    def test_reply_to_broadcast (self):
        with freeze_time("2026-03-19T21:10:23"):
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": True })
            self.assertEqual(response.status_code, 201)
            old_resp = response
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": False, "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json(), { "code": 403, "message": "Cannot reply to broadcasted clarification in non-broadcast mode." })
            response = old_resp
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": False, "reply_to": response.json()["id"] })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), { "code": 400, "message": "Field 'reply_to' must be an integer." })

            response = old_resp
            response = self.run_request("admin", self.contest2.pk, { "text": "some text.", "broadcast": True, "reply_to": int(response.json()["id"]) })
            self.assertEqual(response.status_code, 201)

    def test_reply_to_with_problem_id (self):
        with freeze_time("2026-03-19T21:10:23"):
            problem = Problem.objects.create()
            ContestProblem.objects.create(problem = problem, contest = self.contest2, label = "A")

            response = self.run_request("user2", self.contest2.pk, { "text": "some text." })
            self.assertEqual(response.status_code, 201)
            uuid1 = int(response.json()["id"])
            response = self.run_request("user2", self.contest2.pk, { "text": "some text.", "problem_id": problem.pk })
            self.assertEqual(response.status_code, 201)
            uuid2 = int(response.json()["id"])

            response = self.run_request("admin", self.contest2.pk, { "text": "reply", "reply_to": uuid1 })
            self.assertEqual(response.status_code, 201)
            response = self.run_request("admin", self.contest2.pk, { "text": "reply", "reply_to": uuid1, "problem_id": problem.pk })
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json(), { "code": 403, "message": "Problem of reply should be the same as the original." })
            response = self.run_request("admin", self.contest2.pk, { "text": "reply", "reply_to": uuid2, "problem_id": problem.pk })
            self.assertEqual(response.status_code, 201)
            response = self.run_request("admin", self.contest2.pk, { "text": "reply", "reply_to": uuid2 })
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json(), { "code": 403, "message": "Problem of reply should be the same as the original." })
