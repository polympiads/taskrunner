
import asyncio
from datetime import timedelta
import json

from django.test import TransactionTestCase

from balloons.models import Balloon, BalloonStatus, balloon_status_to_string
from ccs.models.contest import ContestRole
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.contest import ContestManager
from ccs.models.visible import Visibility
from django.contrib.auth.models import User

from problems.models.problem import Problem

class TestBalloonModel (TransactionTestCase):
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

        self.problem1 = Problem.objects.create()
        self.problem2 = Problem.objects.create()

        EventFeed.objects.all().delete()

    def test_create_balloon_as_judge (self):
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.admin, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.admin, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.admin, self.problem2))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.admin, self.problem2))
    def test_create_balloon_as_unregistered (self):
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.user1, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.user1, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.user1, self.problem2))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.user1, self.problem2))
    def test_create_balloon_as_user (self):
        self.assertIsNotNone(Balloon.create_balloon(self.contest1, self.user2, self.problem1))
        self.assertIsNotNone(Balloon.create_balloon(self.contest2, self.user2, self.problem1))
        self.assertIsNotNone(Balloon.create_balloon(self.contest1, self.user2, self.problem2))
        self.assertIsNotNone(Balloon.create_balloon(self.contest2, self.user2, self.problem2))
        
        # Create twice is impossible
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.user2, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.user2, self.problem1))
        self.assertIsNone(Balloon.create_balloon(self.contest1, self.user2, self.problem2))
        self.assertIsNone(Balloon.create_balloon(self.contest2, self.user2, self.problem2))

        for balloon in Balloon.objects.all():
            balloon.set_status(BalloonStatus.PENDING)
        for balloon in Balloon.objects.all():
            balloon.set_status(BalloonStatus.TAKEN)
        for balloon in Balloon.objects.all():
            balloon.set_status(BalloonStatus.TAKEN)
        for balloon in Balloon.objects.all():
            balloon.set_status(BalloonStatus.DROPPED)
        for balloon in Balloon.objects.all():
            balloon.set_status(BalloonStatus.DROPPED)

        feed = list(reversed(list( EventFeed.objects.all() )))
        for kind in [ BalloonStatus.PENDING, BalloonStatus.TAKEN, BalloonStatus.DROPPED ]:
            for contest, problem in [ (self.contest1, self.problem1), (self.contest2, self.problem1), (self.contest1, self.problem2), (self.contest2, self.problem2) ]:
                x_feed = feed.pop()

                self.assertEqual(x_feed.visibility, Visibility.PRIVATE)
                self.assertEqual(x_feed.owner, None)

                balloon = Balloon.objects.get(contest = contest, problem = problem)
                self.assertEqual(
                    json.loads(x_feed.full_payload),
                    { "type": "balloons", "token": str(x_feed.pk), "id": str(balloon.pk), "data": {
                        "id": str(balloon.pk),
                        "problem_id": str(problem.pk),
                        "account_id": str(self.user2.pk),
                        "status": balloon_status_to_string(kind)
                    } })
